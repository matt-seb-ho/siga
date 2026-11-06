"""Claude Code with a SIGA adapter cell, inside the benchmark sandbox.

    siga-bench run --agent siga --cell S+X+M --model MODEL --task ExampleMandel --out DIR

This is the supported way to run the paper's cells. It runs the cell's Claude Code command
(siga_bench/cells.py) in the same bwrap sandbox as every other agent. The agent sees:

  /geos_lib        the task's filtered GEOS tree (no reference deck, no git history)
  /plugins/siga    the adapter directory only: plugin/ (or plugin_evolving/v3/ for SE), read-only.
                   Neither contains benchmark tasks, references or solutions.
  /opt/siga/vector_db   (R cells only) the ChromaDB directory given with --vector-db, read-only
  /home/agent/siga the cell's mcp.json and settings.json

Network: the host CONNECT proxy allows only the Anthropic-compatible gateway host (and, for R,
the embedding API host). The MCP servers run with the agent image's /opt/siga/venv/bin/python
(sandbox/Dockerfile pre-installs their dependencies), because `uv run --script` would need PyPI.

Tools: by default the paper's disallowed list (Skill, AskUserQuestion) plus the sub-agent and
web tools (see cells.STRICT_EXTRA); --paper-tools uses the paper's list only.

Known residual (as in the paper): in R cells the agent can read the ChromaDB files directly. They
hold GEOS documentation chunks and example descriptions, including those of blocked files; the
server filters these out of search results but not out of the raw database. The leak probe
reports the mounted database as a warning.

Metrics: as the claude-code adapter (paper definitions).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from .. import cells, config
from ..sandbox import SandboxSpec, with_relay
from .base import RunContext, api_key, start, wait_socket
from .claude_code import PROXY, ClaudeCodeAdapter

VENV_PYTHON = "/opt/siga/venv/bin/python"
CELL_DIR = "/home/agent/siga"


class SigaCellAdapter(ClaudeCodeAdapter):
    name = "siga"

    def _cell(self, ctx: RunContext) -> dict:
        name = ctx.options.get("cell")
        if not name:
            raise config.ConfigError("--agent siga needs --cell (vanilla, R+S+X+M, S+X, SE, SE-prose, ...)")
        return cells.parse_cell(name)

    def _allow(self, ctx: RunContext, cell: dict) -> list[str]:
        hosts = [urlparse(self._base_url(ctx)).hostname]
        if cell["R"]:
            emb = os.environ.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
            hosts.append(urlparse(emb).hostname)
        return sorted(set(h for h in hosts if h))

    def setup(self, ctx: RunContext) -> None:
        super().setup(ctx)
        cell = self._cell(ctx)
        d = ctx.home / "siga"
        d.mkdir(parents=True, exist_ok=True)
        mcp, settings, env = cells.claude_config(cell, ctx.task_dir, cells.CONTAINER_PLUGIN_ROOT,
                                                 cells.CONTAINER_VECTOR_DB, VENV_PYTHON)
        if mcp is not None:
            (d / "mcp.json").write_text(json.dumps(mcp, indent=2, sort_keys=True))
            (d / "settings.json").write_text(json.dumps(settings, indent=2, sort_keys=True))
        self._env = env
        self._system_prompt = cells.system_prompt(cell)
        (ctx.agent_dir / "system_prompt.md").write_text(self._system_prompt)
        ctx.prompt = cells.user_prompt(cell, cells.task_spec(ctx.task_dir))

    def services(self, ctx: RunContext):
        sock = ctx.sock_dir / "net.sock"
        cmd = [sys.executable, str(PROXY), "--socket", str(sock), "--log", str(ctx.agent_dir / "net.jsonl")]
        for h in self._allow(ctx, self._cell(ctx)):
            cmd += ["--allow", h]
        p = start(cmd, ctx.agent_dir / "proxy.stderr", env={"PATH": "/usr/bin:/bin"})
        wait_socket(sock, [p])
        return [p]

    def sandbox(self, ctx: RunContext, spec: SandboxSpec) -> None:
        cell = self._cell(ctx)
        spec.ro_binds += [(cell["plugin_dir"], cells.CONTAINER_PLUGIN_ROOT)]
        if cell["R"] or cell["X"]:
            venv = config.require("SIGA_ROOTFS", config.ROOTFS, "an unpacked rootfs of sandbox/Dockerfile") / "opt/siga/venv"
            if not venv.is_dir():
                raise config.ConfigError(f"{venv} is missing: rebuild SIGA_ROOTFS from sandbox/Dockerfile")
            spec.ro_binds += [(venv, "/opt/siga/venv")]
        if cell["R"]:
            vdb = ctx.options.get("vector_db") or os.environ.get("SIGA_VECTOR_DB")
            if not vdb:
                raise config.ConfigError("R cells need --vector-db (or SIGA_VECTOR_DB): the ChromaDB dir for R")
            spec.ro_binds += [(Path(vdb), cells.CONTAINER_VECTOR_DB)]
        _, _, env = cells.claude_config(cell, ctx.task_dir, cells.CONTAINER_PLUGIN_ROOT, cells.CONTAINER_VECTOR_DB)
        spec.env.update(env)
        if cell["R"]:
            key = api_key(os.environ.get("SIGA_EMBED_KEY_VAR", "OPENROUTER_API_KEY"))
            spec.env["OPENROUTER_API_KEY"] = key
        super().sandbox(ctx, spec)

    def command(self, ctx: RunContext) -> list[str]:
        cell = self._cell(ctx)
        sp = getattr(self, "_system_prompt", None) or cells.system_prompt(cell)
        argv = ["claude", "-p", "--verbose", "--model", ctx.model, "--append-system-prompt", sp]
        argv += cells.claude_flags(cell, f"{CELL_DIR}/mcp.json", f"{CELL_DIR}/settings.json",
                                   bool(ctx.options.get("paper_tools")))
        return with_relay("net.sock", argv + ["--", ctx.prompt])
