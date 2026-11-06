"""Agent adapters. Add your own: subclass base.Adapter and register it in ADAPTERS."""
from .base import Adapter, RunContext
from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter
from .pi import PiAdapter
from .siga import SigaCellAdapter

ADAPTERS: dict[str, type[Adapter]] = {
    "pi": PiAdapter,
    "codex": CodexAdapter,
    "claude-code": ClaudeCodeAdapter,
    "siga": SigaCellAdapter,
}
