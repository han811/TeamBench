"""
TeamBench framework adapter registry.

External multi-agent frameworks plug into the benchmark by implementing
TeamBenchFrameworkAdapter.  Use create_framework_adapter() to get an
instance by name without importing the optional framework SDKs at the
module level.

Supported framework names:
    "native"    — TeamBench's own orchestrator (no external dependency)
    "autogen"   — Microsoft AutoGen / pyautogen
    "crewai"    — CrewAI
    "langgraph" — LangGraph / LangChain
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.framework_adapter import TeamBenchFrameworkAdapter

# Map framework name -> (module path, class name)
_REGISTRY: dict[str, tuple[str, str]] = {
    "native":    ("harness.frameworks.native_adapter",    "NativeAdapter"),
    "autogen":   ("harness.frameworks.autogen_adapter",   "AutoGenAdapter"),
    "crewai":    ("harness.frameworks.crewai_adapter",    "CrewAIAdapter"),
    "langgraph": ("harness.frameworks.langgraph_adapter", "LangGraphAdapter"),
}


def create_framework_adapter(
    framework: str,
    **kwargs,
) -> "TeamBenchFrameworkAdapter":
    """Factory for framework adapters.

    Args:
        framework: One of 'native', 'autogen', 'crewai', 'langgraph'.
        **kwargs:  Passed directly to the adapter's __init__.  Common keys:
                     model       — LLM model name (e.g. "gpt-4o")
                     temperature — Sampling temperature (default 0.2)
                     max_turns   — Per-agent turn budget (default 30)

    Returns:
        Initialised TeamBenchFrameworkAdapter instance.

    Raises:
        ValueError: Unknown framework name.
        ImportError: Framework SDK not installed.
    """
    key = framework.lower().strip()
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown framework '{framework}'. Available: {available}"
        )

    module_path, class_name = _REGISTRY[key]
    import importlib
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Could not import adapter module '{module_path}' for framework "
            f"'{framework}'. Install the required SDK and try again.\n"
            f"Original error: {exc}"
        ) from exc

    cls = getattr(mod, class_name)
    return cls(**kwargs)


def list_frameworks() -> list[str]:
    """Return the names of all registered framework adapters."""
    return sorted(_REGISTRY.keys())
