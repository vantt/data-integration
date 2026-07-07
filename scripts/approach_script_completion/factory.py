"""factory.py — chọn ApproachScriptCompletionProvider theo tên."""
from __future__ import annotations

from .anthropic_provider import AnthropicCompletionProvider
from .codex_cli_provider import CodexCliCompletionProvider
from .port import ApproachScriptCompletionProvider

_PROVIDERS = {
    "codex": CodexCliCompletionProvider,
    "anthropic": AnthropicCompletionProvider,
}


def get_completion_provider(name: str, **kwargs) -> ApproachScriptCompletionProvider:
    """Trả instance provider theo *name* (default hành vi cũ: "codex").

    kwargs được forward thẳng vào constructor (vd. codex_cmd=... cho "codex").
    """
    try:
        cls = _PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Provider lạ {name!r} — chọn 1 trong {sorted(_PROVIDERS)}") from None
    return cls(**kwargs)
