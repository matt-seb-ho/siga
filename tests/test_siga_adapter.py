"""Tests for the SIGA adapter: the S stop hook, the shipped files, the siga agent and scripts/siga_cell.py."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugin" / "hooks" / "verify_outputs.py"
sys.path.insert(0, str(ROOT / "scripts"))
import siga_cell  # noqa: E402


def run_hook(workspace: Path, **env) -> dict:
    e = {k: v for k, v in os.environ.items() if not k.startswith("GEOS_HOOK")}
    e.update({"GEOS_HOOK_INPUTS_DIR": str(workspace / "inputs")}, **env)
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"stop_hook_active": False}),
                       capture_output=True, text=True, env=e, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_hook_blocks_without_xml_then_gives_up(tmp_path):
    (tmp_path / "inputs").mkdir()
    for _ in range(2):
        out = run_hook(tmp_path)
        assert out["decision"] == "block" and "no .xml files" in out["reason"]
    assert run_hook(tmp_path).get("continue") is True     # GEOS_HOOK_MAX_RETRIES=2 by default
    events = [json.loads(x) for x in (tmp_path / ".verify_hook_events.jsonl").read_text().splitlines()]
    assert [e["reason_category"] for e in events] == ["no_xml", "no_xml", "no_xml_max_retries"]


def test_hook_blocks_on_parse_error_and_allows_clean_deck(tmp_path):
    inp = tmp_path / "inputs"; inp.mkdir()
    (inp / "deck.xml").write_text("<Problem><Mesh></Problem>")
    out = run_hook(tmp_path)
    assert out["decision"] == "block" and "XML parse error in deck.xml" in out["reason"]
    (inp / "deck.xml").write_text("<Problem><Mesh/></Problem>")
    assert run_hook(tmp_path) == {"continue": True, "suppressOutput": True}


def test_hook_disable_switch(tmp_path):
    (tmp_path / "inputs").mkdir()
    assert run_hook(tmp_path, GEOS_HOOK_DISABLE="1").get("continue") is True


@pytest.mark.skipif(shutil.which("xmllint") is None, reason="needs xmllint (libxml2-utils)")
def test_hook_schema_check_with_xmllint(tmp_path):
    xsd = tmp_path / "schema.xsd"
    xsd.write_text("""<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Problem"><xs:complexType><xs:sequence>
    <xs:element name="Mesh" minOccurs="0"/></xs:sequence></xs:complexType></xs:element></xs:schema>""")
    inp = tmp_path / "inputs"; inp.mkdir()
    (inp / "deck.xml").write_text("<Problem><Mesh/><Bogus/></Problem>")
    assert run_hook(tmp_path).get("continue") is True     # parse-only without GEOS_HOOK_XMLLINT
    out = run_hook(tmp_path, GEOS_HOOK_XMLLINT="1", GEOS_HOOK_SCHEMA_PATH=str(xsd))
    assert out["decision"] == "block" and "fail GEOS schema validation" in out["reason"] and "Bogus" in out["reason"]


def test_se_adapter_reuses_s_and_x_unchanged():
    v3 = ROOT / "plugin_evolving" / "v3"
    assert (v3 / "hooks/verify_outputs.py").read_bytes() == HOOK.read_bytes()
    assert (v3 / "scripts/xmllint_mcp.py").read_bytes() == (ROOT / "plugin/scripts/xmllint_mcp.py").read_bytes()
    for rel in ("PRIMER.md", "memory/cheatsheet.md", "skills/copy-dependencies.md",
                "skills/triaxial-driver-setup.md", "agents/dependency-copier.md"):
        assert (v3 / rel).is_file(), rel


def test_plugin_manifests_are_valid_json():
    for p in (ROOT / "plugin/.claude-plugin/plugin.json", ROOT / "plugin/hooks/hooks.json",
              ROOT / "plugin_evolving/v3/.claude-plugin/plugin.json"):
        json.loads(p.read_text())


PAPER_CELLS = {  # cell -> (R, S, X, M) of the paper's factorial (Table 2) plus SE cells
    "vanilla": (0, 0, 0, 0), "R+M": (1, 0, 0, 1), "S+M": (0, 1, 0, 1), "R+S": (1, 1, 0, 0),
    "X+M": (0, 0, 1, 1), "R+X": (1, 0, 1, 0), "S+X": (0, 1, 1, 0), "R+S+X+M": (1, 1, 1, 1),
    "S+X+M": (0, 1, 1, 1), "SE-prose": (0, 1, 1, 0), "SE": (0, 1, 1, 0),
}


@pytest.mark.parametrize("cell", sorted(PAPER_CELLS))
def test_cell_files(cell, tmp_path):
    out = siga_cell.build(cell, "ExampleMandel", "test-model", tmp_path / "c")
    info = json.loads((out / "cell.json").read_text())
    assert tuple(int(info["components"][k]) for k in "RSXM") == PAPER_CELLS[cell]
    sp = (out / "system_prompt.md").read_text()
    up = (out / "prompt.md").read_text()
    assert "# GEOS Primer" in sp and "--- BEGIN SIMULATION SPECIFICATION ---" in up
    assert "Mandel" in up
    run = (out / "run.sh").read_text()
    assert "--disallowedTools Skill --disallowedTools AskUserQuestion --disallowedTools Task" in run
    assert "--disallowedTools WebFetch" in run and "--disallowedTools WebSearch" in run   # strict by default
    assert "refusing to start" in run and "NOT SANDBOXED" in run
    assert subprocess.run(["bash", "-n", str(out / "run.sh")]).returncode == 0
    R, S, X, M = PAPER_CELLS[cell]
    if cell == "vanilla":
        assert not (out / "mcp.json").exists() and "--mcp-config" not in run
        return
    servers = json.loads((out / "mcp.json").read_text())["mcpServers"]
    assert ("geos-rag" in servers) == bool(R) and ("xmllint" in servers) == bool(X)
    assert ("hooks" in json.loads((out / "settings.json").read_text())) == bool(S)
    assert ("GEOS_HOOK_XMLLINT" in info["env"]) == bool(S and X)
    if R:
        excl = json.loads(servers["geos-rag"]["env"]["EXCLUDED_GT_XML_FILENAMES"])
        assert "poroelastic_mandel_benchmark_fim.xml" in excl
    if cell == "SE":
        assert info["adapter_dir_to_mount"] == "plugin_evolving/v3" and info["primer"] == "plugin_evolving/v3/PRIMER.md"
        assert info["prompt_prefix"] is False and info["cheatsheet"] is None
    elif cell == "SE-prose":
        assert info["cheatsheet"] == "plugin_evolving/v3/memory/cheatsheet.md"
        assert info["adapter_dir_to_mount"] == "plugin"
    else:
        assert info["primer"] == "plugin/GEOS_PRIMER_contract.md" and info["adapter_dir_to_mount"] == "plugin"
        assert (info["cheatsheet"] == "plugin/memory_primer_dsv4_m1u.md") == bool(M)
        if M:
            assert (ROOT / "plugin/memory_primer_dsv4_m1u.md").read_text().strip() in sp


def test_paper_tools_and_bad_cell(tmp_path):
    out = siga_cell.build("S+X", "examplemandel", "m", tmp_path / "c", paper_tools=True)
    run = (out / "run.sh").read_text()
    assert "--disallowedTools WebFetch" not in run and "--disallowedTools AskUserQuestion" in run
    with pytest.raises(SystemExit):
        siga_cell.parse_cell("Q")


# ---------------------------------------------------------------- B1: no answers in the agent's view

def _reference_hashes() -> set[str]:
    import hashlib
    tasks = ROOT / "benchmarks/siga-geos/tasks"
    return {hashlib.sha256(f.read_bytes()).hexdigest()
            for f in list(tasks.glob("*/tests/reference/*.xml")) + list(tasks.glob("*/solution/inputs/*.xml"))}


def _assert_no_answers_under(path: Path, refs: set[str]):
    import hashlib
    path = path.resolve()
    tasks = (ROOT / "benchmarks/siga-geos/tasks").resolve()
    assert not (tasks == path or tasks.is_relative_to(path) or path.is_relative_to(tasks)), path
    for f in (path.rglob("*") if path.is_dir() else [path]):
        if f.is_file():
            assert hashlib.sha256(f.read_bytes()).hexdigest() not in refs, f
            assert "tests/reference" not in str(f) and "solution/inputs" not in str(f), f


@pytest.mark.parametrize("cell", sorted(PAPER_CELLS))
def test_siga_agent_sandbox_exposes_no_reference(cell, tmp_path, monkeypatch):
    """Every host path the siga agent binds into its sandbox must be free of reference/solution decks."""
    sys.path.insert(0, str(ROOT / "benchmarks/siga-geos"))
    from siga_bench import config
    from siga_bench.adapters.base import RunContext
    from siga_bench.adapters.siga import SigaCellAdapter
    from siga_bench.sandbox import SandboxSpec
    rootfs = tmp_path / "rootfs"; (rootfs / "opt/siga/venv").mkdir(parents=True)
    vdb = tmp_path / "vdb"; vdb.mkdir()
    monkeypatch.setattr(config, "ROOTFS", rootfs)
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    task_dir = config.task_dir("ExampleMandel")
    out = tmp_path / "run"
    ctx = RunContext(task="ExampleMandel", task_dir=task_dir, model="m", seed=1, out=out,
                     prompt=(task_dir / "instruction.md").read_text(), timeout_s=1,
                     options={"cell": cell, "vector_db": str(vdb)})
    for sub in ("home", "agent", "workspace/inputs"):
        (out / sub).mkdir(parents=True)
    ad = SigaCellAdapter()
    ad.setup(ctx)
    spec = SandboxSpec(geos_lib=tmp_path / "geos", workspace=ctx.workspace, home=ctx.home, sock_dir=tmp_path / "s")
    ad.sandbox(ctx, spec)
    refs = _reference_hashes()
    for src, dst in spec.ro_binds:
        _assert_no_answers_under(Path(src), refs)
        assert dst.startswith(("/plugins/siga", "/opt/")), dst
    _assert_no_answers_under(ctx.home, refs)
    argv = ad.command(ctx)
    assert not any("tests/reference" in a or "solution/inputs" in a or str(ROOT) in a for a in argv)
    for f in ctx.home.rglob("*.json"):
        assert str(ROOT) not in f.read_text()


def test_cell_script_refuses_host_paths_and_in_repo_output(tmp_path):
    with pytest.raises(SystemExit):
        siga_cell.build("S+X", "examplemandel", "m", tmp_path / "c", plugin_root=str(ROOT / "plugin"))
    with pytest.raises(SystemExit):
        siga_cell.main(["--cell", "S+X", "--task", "examplemandel", "--model", "m", "--out", str(ROOT / "cells/x")])
    out = siga_cell.build("R+S+X+M", "examplemandel", "m", tmp_path / "c")
    for f in out.iterdir():
        assert str(ROOT) not in f.read_text(), f


def test_cell_run_sh_refuses_when_a_reference_is_visible(tmp_path):
    """run.sh's guard, pointed at a fake container root: refuses with a reference deck present."""
    out = siga_cell.build("S+X", "examplemandel", "m", tmp_path / "c")
    root = tmp_path / "root"; (root / "geos_lib").mkdir(parents=True)
    stub = tmp_path / "bin"; stub.mkdir(); (stub / "claude").write_text("#!/bin/sh\nexit 0\n"); (stub / "claude").chmod(0o755)
    script = (out / "run.sh").read_text()
    script = (script.replace("find / -xdev", f"find {root}").replace("[[ -d /geos_lib ]]", f"[[ -d {root}/geos_lib ]]")
              .replace("mkdir -p /workspace/inputs\ncd /workspace", f"cd {tmp_path}").replace("/cell/", f"{out}/"))
    (tmp_path / "guarded.sh").write_text(script)
    env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}")
    assert subprocess.run(["bash", str(tmp_path / "guarded.sh")], env=env).returncode == 0
    leak = root / "home/user/siga/benchmarks/siga-geos/tasks/examplemandel/tests/reference"
    leak.mkdir(parents=True)
    shutil.copy(ROOT / "benchmarks/siga-geos/tasks/examplemandel/tests/reference/PoroElastic_Mandel_base.xml", leak)
    r = subprocess.run(["bash", str(tmp_path / "guarded.sh")], env=env, capture_output=True, text=True)
    assert r.returncode == 3 and "refusing to start" in r.stderr
    shutil.rmtree(root / "home")
    (root / "elsewhere").mkdir()      # a renamed dir: caught by the reference file name
    shutil.copy(ROOT / "benchmarks/siga-geos/tasks/examplemandel/solution/inputs/PoroElastic_Mandel_base.xml",
                root / "elsewhere")
    assert subprocess.run(["bash", str(tmp_path / "guarded.sh")], env=env, capture_output=True).returncode == 3


def test_hook_schema_feedback_plumbing_with_stub_xmllint(tmp_path):
    """Runs everywhere: a stub `xmllint` stands in for libxml2 to check how S reports schema errors."""
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    stub = bin_dir / "xmllint"
    stub.write_text("#!/bin/sh\n# args: --schema XSD --noout FILE\n"
                    "echo \"$4:3: element Bogus: Schemas validity error : This element is not expected.\" >&2\n"
                    "echo \"$4 fails to validate\" >&2\nexit 1\n")
    stub.chmod(0o755)
    xsd = tmp_path / "schema.xsd"; xsd.write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>")
    inp = tmp_path / "inputs"; inp.mkdir()
    (inp / "deck.xml").write_text("<Problem><Bogus/></Problem>")
    out = run_hook(tmp_path, GEOS_HOOK_XMLLINT="1", GEOS_HOOK_SCHEMA_PATH=str(xsd),
                   PATH=f"{bin_dir}:{os.environ.get('PATH', '')}")
    assert out["decision"] == "block"
    assert "- deck.xml:\n  deck.xml:3: element Bogus" in out["reason"] and "fails to validate" not in out["reason"]
    assert f"xmllint --schema {xsd} --noout <file>.xml" in out["reason"]
