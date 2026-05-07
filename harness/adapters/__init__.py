"""
TeamBench provider adapters.

Each adapter implements ToolCallAdapter from harness.agent_interface.
Import the adapter you need; only that provider's SDK is required.

Available adapters:
  - GeminiAdapter   (harness.gemini_adapter)          requires: google-genai
  - OpenAIAdapter   (harness.adapters.openai_adapter) requires: openai
  - AnthropicAdapter(harness.adapters.anthropic_adapter) requires: anthropic
"""
from __future__ import annotations


def create_adapter(model: str, temperature: float = 0.2, **kwargs):
    """Factory: instantiate the correct adapter based on model name prefix.

    Supported prefixes:
      gemini-*   -> GeminiAdapter  (GEMINI_API_KEY)
      gpt-* / o* -> OpenAIAdapter  (OPENAI_API_KEY)
      claude-*   -> AnthropicAdapter (ANTHROPIC_API_KEY)
      vllm:*     -> OpenAIAdapter with local vLLM base_url
                    Format: vllm:<model-name> or vllm:<model-name>@<base_url>
                    Default base_url: http://localhost:8000/v1
                    Env override: VLLM_BASE_URL
    """
    model_lower = model.lower()

    if model_lower.startswith("gemini"):
        from harness.gemini_adapter import GeminiAdapter
        return GeminiAdapter(model=model, temperature=temperature, **kwargs)

    if model_lower.startswith(("gpt-", "o1", "o3", "o4")):
        from harness.adapters.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(model=model, temperature=temperature, **kwargs)

    if model_lower.startswith("claude"):
        from harness.adapters.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(model=model, temperature=temperature, **kwargs)

    if model_lower.startswith("mock"):
        from harness.adapters.mock_adapter import MockAdapter
        return MockAdapter(temperature=temperature, **kwargs)

    if model_lower.startswith("openrouter:"):
        import os, pathlib
        from harness.adapters.openai_adapter import OpenAIAdapter
        # Parse openrouter:<model>  (model id is the OpenRouter model slug,
        # e.g. openai/gpt-oss-120b, qwen/qwen-3-8b, meta-llama/llama-3.1-405b).
        or_model = model[len("openrouter:"):]
        base_url = "https://openrouter.ai/api/v1"
        # Read OPENROUTER_API or OPENROUTER_API_KEY from env or local .env
        api_key = (os.environ.get("OPENROUTER_API")
                   or os.environ.get("OPENROUTER_API_KEY"))
        if not api_key:
            env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("OPENROUTER_API") and "=" in line:
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not api_key:
            raise ValueError(
                "OpenRouter route requires OPENROUTER_API in env or .env"
            )
        max_tokens = int(os.environ.get("OPENROUTER_MAX_TOKENS", "8192"))
        print(f"  [openrouter] model={or_model}, max_tokens={max_tokens}")
        return OpenAIAdapter(
            model=or_model,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
            max_tokens=max_tokens,
            lenient_mode=True,
            **kwargs,
        )

    if model_lower.startswith("vllm:"):
        import os
        from harness.adapters.openai_adapter import OpenAIAdapter
        # Parse vllm:<model>@<url> or vllm:<model>
        spec = model[5:]  # strip "vllm:"
        if "@" in spec:
            vllm_model, base_url = spec.rsplit("@", 1)
        else:
            vllm_model = spec
            base_url = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
        # Allow env var overrides; default max_tokens raised to 8192 for reasoning models
        default_max_tokens = int(os.environ.get("VLLM_MAX_TOKENS", "8192"))
        max_tokens = kwargs.pop("max_tokens", default_max_tokens)
        context_window = int(os.environ.get("VLLM_CONTEXT_WINDOW", "32768"))
        print(f"  [vllm] model={vllm_model}, base_url={base_url}, "
              f"max_tokens={max_tokens}, context_window={context_window}")
        return OpenAIAdapter(
            model=vllm_model,
            temperature=temperature,
            base_url=base_url,
            max_tokens=max_tokens,
            lenient_mode=True,
            **kwargs,
        )

    raise ValueError(
        f"Cannot determine adapter for model '{model}'. "
        "Use a model name starting with 'gemini-', 'gpt-', 'o1', 'o3', 'o4', 'claude-', 'mock', or 'vllm:'."
    )
