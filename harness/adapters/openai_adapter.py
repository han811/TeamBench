"""
OpenAI adapter for TeamBench agent driver.

Implements ToolCallAdapter using the `openai` Python SDK.
Supports GPT-4o, GPT-4-turbo, GPT-5-nano, GPT-5-mini, o1, o3, and other OpenAI chat models.

Requires: pip install openai
API key:  OPENAI_API_KEY environment variable or .env
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from harness.agent_interface import AdapterResponse, ModelAdapter, ToolCallAdapter


_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")
_INLINE_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from model output."""
    return _THINK_TAG_RE.sub("", text).strip()


def _sanitize_tool_args(raw: str) -> dict:
    """Try multiple strategies to parse tool call arguments from a raw string.

    Handles common open-source model issues: trailing commas, markdown
    code fences, and minor JSON formatting errors.
    """
    if not raw:
        return {}

    # Strategy 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip thinking tags then parse
    cleaned = _strip_thinking(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: extract from markdown code block
    m = _CODE_BLOCK_RE.search(cleaned)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 4: fix trailing commas then parse
    fixed = _TRAILING_COMMA_RE.sub(r"\1", cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Strategy 5: find the outermost {...} blob
    m2 = _INLINE_JSON_RE.search(fixed)
    if m2:
        try:
            return json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: return raw string under a reserved key
    return {"_raw": raw}


def _extract_tool_calls_from_text(text: str) -> list[dict]:
    """Try to extract tool calls embedded in plain text.

    Some open-source models emit tool calls as JSON in their text
    response instead of using the structured tool_calls field.
    Supported shapes:
      {"name": "...", "args": {...}}
      {"tool_name": "...", "arguments": {...}}
    """
    results = []
    cleaned = _strip_thinking(text)
    # Look for all {...} blobs that look like tool calls
    for m in _INLINE_JSON_RE.finditer(cleaned):
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            # Try fixing trailing commas
            candidate = _TRAILING_COMMA_RE.sub(r"\1", m.group(0))
            try:
                obj = json.loads(candidate)
            except json.JSONDecodeError:
                continue
        if not isinstance(obj, dict):
            continue
        # Shape 1: {"name": "...", "args": {...}}
        if "name" in obj and isinstance(obj.get("args"), dict):
            results.append({"name": obj["name"], "args": obj["args"]})
        # Shape 2: {"tool_name": "...", "arguments": {...}}
        elif "tool_name" in obj and isinstance(obj.get("arguments"), dict):
            results.append({"name": obj["tool_name"], "args": obj["arguments"]})
    return results


def _standard_to_openai_functions(tools: list[dict]) -> list[dict]:
    """Convert standard tool declarations to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


def _load_all_openai_keys() -> list[str]:
    """Load all OPENAI_API_KEY* values from local .env."""
    keys = []
    seen = set()
    for env_path in [".env"]:
        if not os.path.exists(env_path):
            continue
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY") and "=" in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val not in seen:
                        keys.append(val)
                        seen.add(val)
    env_key = os.environ.get("OPENAI_API_KEY", "")
    if env_key and env_key not in seen:
        keys.insert(0, env_key)
    return keys


class OpenAIAdapter(ModelAdapter, ToolCallAdapter):
    """OpenAI GPT/o-series adapter for TeamBench.

    Uses the openai >= 1.0 SDK with the chat completions API and
    parallel function calling. Supports API key rotation for resilience.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 8192,
        base_url: str | None = None,
        lenient_mode: bool = False,
    ):
        try:
            import openai
            self._openai = openai
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAIAdapter. "
                "Install it with: pip install openai"
            ) from exc

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.lenient_mode = lenient_mode
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._is_or_anthropic = bool(
            base_url and "openrouter.ai" in base_url
            and model.startswith("anthropic/")
        )
        if self._is_or_anthropic:
            print(f"  [openrouter-anthropic] prompt caching enabled for {model}")

        if base_url:
            # Local server (vLLM, etc.) — no real API key needed
            self._keys = [api_key or "dummy"]
        elif api_key:
            self._keys = [api_key]
        else:
            self._keys = _load_all_openai_keys()
        if not self._keys:
            raise ValueError(
                "No OPENAI_API_KEY found. Provide api_key or set the environment variable."
            )
        self._key_index = 0
        client_kwargs: dict[str, Any] = {"api_key": self._keys[0]}
        if base_url:
            client_kwargs["base_url"] = base_url
            # Timeout for local vLLM servers to avoid hung requests
            client_kwargs["timeout"] = 300.0  # 5 minutes
        self._client = self._openai.OpenAI(**client_kwargs)
        if len(self._keys) > 1:
            print(f"  [openai] Loaded {len(self._keys)} API keys for rotation")
        if base_url:
            print(f"  [openai] Using custom base_url: {base_url}")

    def _rotate_key(self) -> None:
        """Switch to the next API key in the rotation."""
        if len(self._keys) <= 1:
            return
        self._key_index = (self._key_index + 1) % len(self._keys)
        client_kwargs: dict[str, Any] = {"api_key": self._keys[self._key_index]}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = self._openai.OpenAI(**client_kwargs)

    # ------------------------------------------------------------------
    # ModelAdapter (simple text generation)
    # ------------------------------------------------------------------

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Simple text generation (ModelAdapter contract)."""
        oai_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "tool":
                role = "user"
            oai_messages.append({"role": role, "content": msg.get("content", "")})

        api_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
        }
        # GPT-5 and o-series use max_completion_tokens; older models use max_tokens
        if self.model.startswith(("gpt-5", "o1", "o3", "o4")):
            api_kwargs["max_completion_tokens"] = self.max_tokens
        else:
            api_kwargs["max_tokens"] = self.max_tokens
        if not self.model.startswith(("o1", "o3", "o4", "gpt-5")):
            api_kwargs["temperature"] = self.temperature

        response = self._call_with_retry(**api_kwargs)
        self._track_usage(response)
        choice = response.choices[0] if response.choices else None
        return (choice.message.content or "") if choice else ""

    # ------------------------------------------------------------------
    # ToolCallAdapter interface
    # ------------------------------------------------------------------

    def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
    ) -> AdapterResponse:
        """Call OpenAI chat completions with function calling and return AdapterResponse."""
        oai_messages = self._build_messages(messages, system_prompt)
        oai_tools = _standard_to_openai_functions(tools) if tools else None

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
        }
        # GPT-5 and o-series use max_completion_tokens; older models use max_tokens
        if self.model.startswith(("gpt-5", "o1", "o3", "o4")):
            kwargs["max_completion_tokens"] = self.max_tokens
        else:
            kwargs["max_tokens"] = self.max_tokens
        # o-series and GPT-5 models do not support custom temperature
        if not self.model.startswith(("o1", "o3", "o4", "gpt-5")):
            kwargs["temperature"] = self.temperature
        if oai_tools:
            kwargs["tools"] = oai_tools
            kwargs["tool_choice"] = "auto"

        response = self._call_with_retry(**kwargs)
        self._track_usage(response)
        return self._parse_response(response)

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

    def _build_messages(self, messages: list[dict], system_prompt: str) -> list[dict]:
        """Prepend system prompt and convert roles to OpenAI format.

        Merges consecutive same-role messages to satisfy chat templates
        that require strict user/assistant alternation (e.g., Gemma).
        """
        oai: list[dict] = []
        if system_prompt:
            oai.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # "tool" role in standard format -> "user" in OpenAI
            if role == "tool":
                role = "user"
            # Merge consecutive same-role messages
            if oai and oai[-1]["role"] == role:
                oai[-1]["content"] += "\n\n" + content
            else:
                oai.append({"role": role, "content": content})

        # For OpenRouter→Anthropic routes, mark the first system and first
        # user message as cache breakpoints (Anthropic allows up to 4;
        # 2 covers the stable system prompt + task spec prefix).
        if self._is_or_anthropic:
            marked = 0
            for m in oai:
                if marked >= 2:
                    break
                if m["role"] in ("system", "user") and isinstance(m["content"], str):
                    m["content"] = [{
                        "type": "text",
                        "text": m["content"],
                        "cache_control": {"type": "ephemeral"},
                    }]
                    marked += 1
        return oai

    def _parse_response(self, response: Any) -> AdapterResponse:
        """Parse an OpenAI ChatCompletion into AdapterResponse."""
        text = ""
        tool_calls: list[dict] = []

        choice = response.choices[0] if response.choices else None
        if not choice:
            return AdapterResponse()

        msg = choice.message
        if msg.content:
            text = msg.content

        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = _sanitize_tool_args(tc.function.arguments or "")
                tool_calls.append({"name": tc.function.name, "args": args})

        # Lenient mode: strip reasoning tokens from text, then try to recover
        # tool calls embedded in the text (common open-source model behavior).
        if self.lenient_mode:
            text = _strip_thinking(text)
            if not tool_calls and text:
                recovered = _extract_tool_calls_from_text(text)
                if recovered:
                    tool_calls = recovered

        done = "DONE" in text or "TASK_COMPLETE" in text
        return AdapterResponse(text=text, tool_calls=tool_calls, done=done)

    def _call_with_retry(self, max_retries: int = 8, **kwargs) -> Any:
        """Call OpenAI API with exponential backoff and key rotation."""
        # Force direct Anthropic routing on OR so cache_control is preserved
        # (Bedrock/Google fallbacks don't honor Anthropic prompt caching).
        if self._is_or_anthropic:
            extra = kwargs.get("extra_body") or {}
            extra.setdefault("provider", {"order": ["anthropic"], "allow_fallbacks": False})
            kwargs["extra_body"] = extra
        for attempt in range(max_retries):
            try:
                return self._client.chat.completions.create(**kwargs)
            except Exception as e:
                error_str = str(e).lower()
                retryable = ("429" in error_str or "rate" in error_str
                             or "503" in error_str or "unavailable" in error_str
                             or "overloaded" in error_str or "server_error" in error_str
                             or "timeout" in error_str)
                if retryable:
                    self._rotate_key()
                    wait = min(2 ** attempt * 2, 120)
                    key_info = f" (key {self._key_index + 1}/{len(self._keys)})" if len(self._keys) > 1 else ""
                    print(f"  [retry] {attempt + 1}/{max_retries} in {wait}s{key_info}...")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"OpenAI API failed after {max_retries} retries")

    def _track_usage(self, response: Any) -> None:
        """Accumulate token counts from response usage."""
        usage = getattr(response, "usage", None)
        if usage:
            self._total_input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self._total_output_tokens += getattr(usage, "completion_tokens", 0) or 0
