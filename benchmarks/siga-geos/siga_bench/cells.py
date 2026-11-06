"""SIGA cells: how the paper's runner configured Claude Code for one adapter configuration.

A SIGA cell is a subset of the four adapter components (paper Sec. 3):

  R  retrieval MCP server         plugin/scripts/geos_rag_mcp.py
  S  validation Stop hook         plugin/hooks/verify_outputs.py
  X  validator MCP tool           plugin/scripts/xmllint_mcp.py
  M  procedural-memory cheatsheet plugin/memory_primer_dsv4_m1u.md (appended to the system prompt)

plus the self-evolved cells SE (plugin_evolving/v3 as the adapter) and SE-prose (S+X with
v3's primer and cheatsheet). Cell names: vanilla, any combination of the letters R S X M
(e.g. "S+X", "RSXM"), SE, SE-prose.

This module builds the system prompt, the task prompt, the Stop-hook settings and the MCP
config as the paper's runner did. The prompts were checked byte for byte against that runner's
prompt code for all 11 paper cells. The settings and MCP configs equal the ones saved by the
paper's runs, with the plugin and database paths substituted. Details:

  * S checks parse errors only, unless X is also on; then the hook also runs
    `xmllint --schema` (GEOS_HOOK_XMLLINT=1), as in the paper's S+X cells.
  * Whenever any component is on (except SE), the task prompt is prefixed with
    plugin/prompts/native_plugin_prefix.txt, which names the RAG tools even in cells
    without R. The system prompt gets plugin/prompts/rag_instructions.txt when R is on
    and rag_vanilla.txt otherwise. Neither names the X tool. All are kept verbatim.
  * The paper disallowed only Skill and AskUserQuestion. Here the default also disallows
    sub-agent and web tools (STRICT_EXTRA): model-side web search can reach GitHub, which
    hosts every reference deck. Pass paper_tools=True for the paper's list.

It only produces configuration. `siga-bench run --agent siga --cell CELL` runs a cell inside
the benchmark sandbox (adapters/siga.py); scripts/siga_cell.py writes the files for use inside
your own isolated container.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config

PLUGIN = config.REPO_ROOT / "plugin"
SE_PLUGIN = config.REPO_ROOT / "plugin_evolving" / "v3"
PROMPTS = PLUGIN / "prompts"

PAPER_DISALLOWED = ("Skill", "AskUserQuestion")
STRICT_EXTRA = ("Task", "Agent", "TaskCreate", "WebFetch", "WebSearch",
                "Workflow", "SendMessage", "CronCreate", "CronDelete", "CronList", "ScheduleWakeup",
                "EnterWorktree", "ExitWorktree", "RemoteTrigger")
CONTAINER_SCHEMA = "/geos_lib/src/coreComponents/schema/schema.xsd"
CONTAINER_PLUGIN_ROOT = "/plugins/siga"
CONTAINER_VECTOR_DB = "/opt/siga/vector_db"


def parse_cell(name: str) -> dict:
    """The cell's switches: R, S, X, M, plugin_dir, primer, cheatsheet, prefix, plugin_enabled."""
    key = name.strip()
    base = {"name": key, "R": False, "S": False, "X": False, "M": False, "plugin_dir": PLUGIN,
            "primer": PLUGIN / "GEOS_PRIMER_contract.md", "cheatsheet": None, "prefix": None}
    if key.lower() == "vanilla":
        pass
    elif key.lower() == "se":
        base.update(S=True, X=True, plugin_dir=SE_PLUGIN, primer=SE_PLUGIN / "PRIMER.md", prefix=False)
    elif key.lower() == "se-prose":
        base.update(S=True, X=True, primer=SE_PLUGIN / "PRIMER.md",
                    cheatsheet=SE_PLUGIN / "memory" / "cheatsheet.md")
    else:
        letters = re.sub(r"[\s+,]", "", key.upper())
        if not letters or set(letters) - set("RSXM"):
            raise SystemExit(f"unknown cell {name!r}: use vanilla, SE, SE-prose or letters from RSXM")
        base.update({c: True for c in letters})
        if base["M"]:
            base["cheatsheet"] = PLUGIN / "memory_primer_dsv4_m1u.md"
    base["plugin_enabled"] = key.lower() != "vanilla"
    if base["prefix"] is None:
        base["prefix"] = base["plugin_enabled"]
    return base


def task_spec(task_dir: Path) -> str:
    text = (task_dir / "instruction.md").read_text()
    a, b = "--- BEGIN SIMULATION SPECIFICATION ---\n", "\n--- END SIMULATION SPECIFICATION ---"
    return text.split(a, 1)[1].split(b, 1)[0].strip()


def blocked_for_rag(task_dir: Path) -> tuple[list[str], list[str]]:
    rels = [ln.strip() for ln in (task_dir / "environment" / "blocked_files.txt").read_text().splitlines()
            if ln.strip()]
    xml = sorted({Path(r).name.lower() for r in rels if r.lower().endswith(".xml")})
    rst = sorted(r for r in rels if r.lower().endswith(".rst"))
    return xml, rst


def reference_basenames(task_dir: Path) -> list[str]:
    return sorted(p.name for p in (task_dir / "tests" / "reference").glob("*.xml"))


def system_prompt(cell: dict) -> str:
    contract = (PROMPTS / "agents_contract.md").read_text()
    primer = cell["primer"].read_text().strip()
    text = f"{contract.strip()}\n\n---\n# GEOS Primer\n\n{primer}\n"
    if cell["cheatsheet"] is not None:
        body = cell["cheatsheet"].read_text().strip()
        if body:
            text += f"\n\n---\n{body}\n"
    rag = (PROMPTS / ("rag_instructions.txt" if cell["R"] else "rag_vanilla.txt")).read_text()
    return text + "\n\n---\n" + rag + (PROMPTS / "real_tool_tail.txt").read_text()


def user_prompt(cell: dict, spec: str) -> str:
    body = f"--- BEGIN SIMULATION SPECIFICATION ---\n{spec}\n--- END SIMULATION SPECIFICATION ---"
    return ((PROMPTS / "native_plugin_prefix.txt").read_text() + body) if cell["prefix"] else body


def _server(script: str, env: dict, mcp_python: str | None) -> dict:
    if mcp_python:
        cmd, args = mcp_python, [script]
    else:
        cmd, args = "uv", ["run", "--script", script]
    return {"type": "stdio", "command": cmd, "args": args, "env": env}


def claude_config(cell: dict, task_dir: Path, plugin_root: str, vector_db: str,
                  mcp_python: str | None = None) -> tuple[dict | None, dict | None, dict]:
    """(mcp.json, settings.json, env) for the cell; the JSONs are None for vanilla.
    All paths are as the agent sees them (plugin_root is the adapter dir's mount point)."""
    env: dict[str, str] = {}
    if not cell["plugin_enabled"]:
        return None, None, env
    servers = {}
    if cell["R"]:
        xml, rst = blocked_for_rag(task_dir)
        servers["geos-rag"] = _server(f"{plugin_root}/scripts/geos_rag_mcp.py", {
            "CLAUDE_PLUGIN_ROOT": plugin_root, "GEOS_VECTOR_DB_DIR": vector_db,
            "EXCLUDED_GT_XML_FILENAMES": json.dumps(xml), "EXCLUDED_RST_PATHS": json.dumps(rst)}, mcp_python)
    if cell["X"]:
        servers["xmllint"] = _server(f"{plugin_root}/scripts/xmllint_mcp.py", {
            "CLAUDE_PLUGIN_ROOT": plugin_root, "XMLLINT_SCHEMA_PATH": CONTAINER_SCHEMA}, mcp_python)
    settings: dict = {}
    if cell["S"]:
        settings["hooks"] = {"Stop": [{"matcher": "", "hooks": [
            {"type": "command", "command": f"python3 {plugin_root}/hooks/verify_outputs.py", "timeout": 30}]}]}
    env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    if cell["S"] and cell["X"]:
        env["GEOS_HOOK_XMLLINT"] = "1"
    return {"mcpServers": servers}, settings, env


def disallowed_tools(paper_tools: bool = False) -> tuple[str, ...]:
    return PAPER_DISALLOWED + (() if paper_tools else STRICT_EXTRA)


def claude_flags(cell: dict, mcp_path: str, settings_path: str, paper_tools: bool = False) -> list[str]:
    """Claude Code flags after `claude -p --verbose --model M --append-system-prompt SP`."""
    f = ["--tools", "default"]
    for t in disallowed_tools(paper_tools):
        f += ["--disallowedTools", t]
    if cell["plugin_enabled"]:
        f += [f"--mcp-config={mcp_path}", "--strict-mcp-config", "--settings", settings_path]
    return f + ["--output-format", "stream-json", "--permission-mode", "bypassPermissions"]
