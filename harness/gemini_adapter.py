"""
Gemini adapter for TeamBench agent driver.

Uses the google-genai SDK (GA package) with manual function calling.
Implements ToolCallAdapter so agent_loop.py has zero provider-specific code.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

from google import genai
from google.genai import types

from harness.agent_interface import AdapterResponse, ModelAdapter, ToolCallAdapter


def _standard_to_gemini_declarations(tools: list[dict]) -> list[types.Tool]:
    """Convert standard tool declarations (dicts) to Gemini FunctionDeclaration objects."""
    declarations = []
    for t in tools:
        params = t.get("parameters", {})
        props = params.get("properties", {})
        required = params.get("required", [])

        gemini_props = {
            k: types.Schema(type=v.get("type", "STRING").upper(), description=v.get("description", ""))
            for k, v in props.items()
        }

        declarations.append(types.FunctionDeclaration(
            name=t["name"],
            description=t.get("description", ""),
            parameters=types.Schema(
                type="OBJECT",
                properties=gemini_props,
                required=required,
            ),
        ))
    return [types.Tool(function_declarations=declarations)]


def _load_all_gemini_keys() -> list[str]:
    """Load all GEMINI_API_KEY* values from local .env."""
    keys = []
    seen = set()
    for env_path in [".env"]:
        if not os.path.exists(env_path):
            continue
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val not in seen:
                        keys.append(val)
                        seen.add(val)
    # Also check environment variable
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and env_key not in seen:
        keys.insert(0, env_key)
    return keys


class GeminiAdapter(ModelAdapter, ToolCallAdapter):
    """Gemini model adapter with tool calling support.

    Implements both ModelAdapter (simple text generation) and
    ToolCallAdapter (standard tool-calling interface used by AgentLoop).
    Supports API key rotation across multiple keys for resilience against 503 errors.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.2,
        max_output_tokens: int = 8192,
    ):
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        if api_key:
            self._keys = [api_key]
        else:
            self._keys = _load_all_gemini_keys()
        if not self._keys:
            raise ValueError("No GEMINI_API_KEY found. Provide api_key or set the environment variable.")
        # Skip key validation at init (too slow with many keys + rate limits).
        # Invalid keys will be rotated away at runtime via _call_with_retry.
        self._key_index = 0
        self.client = genai.Client(api_key=self._keys[0])
        if len(self._keys) > 1:
            print(f"  [gemini] Loaded {len(self._keys)} valid API keys for rotation")

    def _rotate_key(self) -> None:
        """Switch to the next API key in the rotation."""
        if len(self._keys) <= 1:
            return
        self._key_index = (self._key_index + 1) % len(self._keys)
        self.client = genai.Client(api_key=self._keys[self._key_index])

    # ------------------------------------------------------------------
    # ModelAdapter (simple text generation)
    # ------------------------------------------------------------------

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Simple text generation (ModelAdapter contract)."""
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
            elif msg["role"] == "assistant":
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))

        response = self._call_with_retry(
            contents=contents,
            system_instruction=system_instruction,
        )
        self._track_usage(response)
        return response.text or ""

    # ------------------------------------------------------------------
    # ToolCallAdapter (provider-agnostic tool-calling interface)
    # ------------------------------------------------------------------

    def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
    ) -> AdapterResponse:
        """Convert standard messages/tools to Gemini format, call API, return AdapterResponse."""
        gemini_tools = _standard_to_gemini_declarations(tools) if tools else None
        contents = self._messages_to_gemini(messages)

        try:
            raw = self._call_with_retry(
                contents=contents,
                system_instruction=system_prompt or None,
                tools=gemini_tools,
            )
            self._track_usage(raw)
            return self._parse_response(raw)
        except Exception as e:
            err = str(e).lower()
            retryable = (
                "429" in err or "resource_exhausted" in err
                or "rate" in err or "503" in err or "unavailable" in err
                or "gemini api failed after" in err
            )
            if not retryable:
                raise
            print(
                f"  [gemini→openrouter-fallback] direct exhausted: {str(e)[:120]}"
            )
            return self._openrouter_fallback(messages, system_prompt, tools)

    def _openrouter_fallback(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
    ) -> AdapterResponse:
        """Route to OpenRouter when all direct Gemini keys are rate-limited.

        OR's Google provider hits the same underlying model weights; the only
        methodological shift is the intermediate proxy. Token usage is merged
        into self._total_{input,output}_tokens so role_usage remains accurate.
        """
        if not hasattr(self, "_or_fallback"):
            from harness.adapters import create_adapter
            or_model = f"openrouter:google/{self.model}"
            self._or_fallback = create_adapter(
                or_model, temperature=self.temperature,
            )
            self._or_prev_in = 0
            self._or_prev_out = 0
        resp = self._or_fallback.generate_with_tools(
            messages, system_prompt, tools,
        )
        try:
            usage = self._or_fallback.get_usage() or {}
            cur_in = int(usage.get("input_tokens", 0) or 0)
            cur_out = int(usage.get("output_tokens", 0) or 0)
            self._total_input_tokens += max(0, cur_in - self._or_prev_in)
            self._total_output_tokens += max(0, cur_out - self._or_prev_out)
            self._or_prev_in = cur_in
            self._or_prev_out = cur_out
        except Exception:  # noqa: BLE001
            pass
        return resp

    def get_usage(self) -> dict:
        """Return cumulative token usage."""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "model": self.model,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _messages_to_gemini(self, messages: list[dict]) -> list[types.Content]:
        """Convert standard message dicts to Gemini Content objects.

        Roles: "user" -> "user", "assistant" -> "model", "tool" -> "user" (function response).
        """
        contents: list[types.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)],
                ))
            elif role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)],
                ))
            elif role == "tool":
                # Tool result injected as user turn text (already formatted by agent_loop)
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)],
                ))
        return contents

    def _parse_response(self, response: types.GenerateContentResponse) -> AdapterResponse:
        """Parse a Gemini response into an AdapterResponse.

        Skip thought parts (part.thought=True) so private reasoning never leaks
        into surfaced text or triggers DONE detection. Native-thinking models
        (gemini-2.5-pro etc.) emit thoughts as separate parts; without this
        filter, thinking text containing "DONE" would prematurely terminate
        the agent loop.
        """
        text = ""
        tool_calls: list[dict] = []

        for candidate in response.candidates or []:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if getattr(part, "thought", False):
                    continue
                if part.text:
                    text += part.text
                if part.function_call:
                    fc = part.function_call
                    tool_calls.append({
                        "name": fc.name,
                        "args": dict(fc.args) if fc.args else {},
                    })

        done = "DONE" in text or "TASK_COMPLETE" in text
        return AdapterResponse(text=text, tool_calls=tool_calls, done=done)

    def _call_with_retry(
        self,
        contents: list[types.Content],
        system_instruction: str | None = None,
        tools: list[types.Tool] | None = None,
        max_retries: int = 15,
    ) -> types.GenerateContentResponse:
        """Call Gemini API with exponential backoff and key rotation for 503/429 errors."""
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            tools=tools,
        )
        # gemini-2.5-pro enters thinking-only states under tool-loop pressure
        # (empty text + empty function_call parts), causing stuck-detection to
        # kill the agent. Disable native thinking for that family. Gemini 3.x
        # tolerates the loop with thinking on, so leave it untouched.
        if "2.5-pro" in self.model:
            config.thinking_config = types.ThinkingConfig(thinking_budget=0)
        if system_instruction:
            config.system_instruction = system_instruction

        for attempt in range(max_retries):
            try:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                error_str = str(e).lower()
                retryable = ("429" in error_str or "resource_exhausted" in error_str
                             or "rate" in error_str or "503" in error_str
                             or "unavailable" in error_str
                             or "api key not valid" in error_str)
                if retryable:
                    self._rotate_key()
                    wait = min(2 ** attempt * 2, 300)
                    key_info = f" (key {self._key_index + 1}/{len(self._keys)})" if len(self._keys) > 1 else ""
                    print(f"  [retry] {attempt + 1}/{max_retries} in {wait}s{key_info}...")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"Gemini API failed after {max_retries} retries")

    def _track_usage(self, response: types.GenerateContentResponse) -> None:
        """Track token usage from response metadata."""
        meta = getattr(response, "usage_metadata", None)
        if meta:
            self._total_input_tokens += getattr(meta, "prompt_token_count", 0) or 0
            self._total_output_tokens += getattr(meta, "candidates_token_count", 0) or 0


# ---------------------------------------------------------------------------
# Legacy helper kept for any external code that imported it directly
# ---------------------------------------------------------------------------

def tools_to_gemini_declarations(tools: list) -> list[types.Tool]:
    """Backward-compat shim: convert Tool objects to Gemini declarations.

    Prefer tools_to_standard_declarations() + GeminiAdapter.generate_with_tools()
    for new code.
    """
    from harness.agent_interface import tools_to_standard_declarations
    std = tools_to_standard_declarations(tools)
    return _standard_to_gemini_declarations(std)
