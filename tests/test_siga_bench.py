"""Tests for benchmarks/siga-geos (siga-bench): task export, verifier, scorers, adapters, sandbox.

Everything here runs without GEOS, Docker or network except the two tests marked
`needs GEOS` (set SIGA_GEOS_SRC) and the leak probe (also needs bwrap, SIGA_ROOTFS and Codex).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "siga-geos"
sys.path.insert(0, str(BENCH))

from siga_bench import config  # noqa: E402
from siga_bench.net.connect_proxy import host_allowed  # noqa: E402

HAVE_GEOS = config.GEOS_SRC is not None and config.GEOS_SRC.exists()
HAVE_SANDBOX = (HAVE_GEOS and shutil.which("bwrap") is not None and config.ROOTFS is not None
                and (config.ROOTFS / "usr").exists())
ALL = config.SPLITS["all"]
SCORERS = ("paper", "fixed")


def test_task_sets_match_paper():
    assert len(config.VAL17) == 17 and len(config.HELDOUT10) == 10
    assert not set(config.VAL17) & set(config.HELDOUT10)
    dirs = sorted(p.name for p in config.TASKS_DIR.iterdir() if p.is_dir())
    assert dirs == sorted(config.task_id(n) for n in ALL)
    manifest = json.loads((config.TASKS_DIR / "manifest.json").read_text())
    assert manifest["tasks"] == [config.task_id(n) for n in ALL]
    assert manifest["geos_commit"] == config.GEOS_UPSTREAM_COMMIT


@pytest.mark.parametrize("name", ALL)
def test_exported_task_layout(name):
    d = config.TASKS_DIR / config.task_id(name)
    for rel in ("task.toml", "instruction.md", "environment/Dockerfile", "environment/blocked_files.txt",
                "tests/test.sh", "tests/score.py", "tests/judge_geos_paper.py", "tests/judge_geos_fixed.py",
                "solution/solve.sh"):
        assert (d / rel).is_file(), rel
    refs = sorted(p.name for p in (d / "tests/reference").glob("*.xml"))
    assert refs and refs == sorted(p.name for p in (d / "solution/inputs").glob("*.xml"))
    toml = (d / "task.toml").read_text()
    assert 'schema_version = "1.4"' in toml and f'siga_task = "{name}"' in toml
    assert 'network_mode = "allowlist"' in toml and "github" not in toml
    assert 'allowed_hosts = ["set-your-model-api-host.invalid"]' in toml   # fails closed until edited
    assert "UNTESTED UNDER HARBOR" in toml
    assert config.GEOS_UPSTREAM_COMMIT in (d / "environment/Dockerfile").read_text()
    assert 'SIGA_SCORER:-paper' in (d / "tests/test.sh").read_text()
    # the agent-visible instruction never names the reference files' location
    text = (d / "instruction.md").read_text()
    assert not any(x in text for x in ("tests/reference", "/solution", "experiments_gt", "blocked_files"))


def test_reference_sha256_scheme():
    import hashlib, re
    for name in ALL:
        d = config.task_dir(name)
        h = hashlib.sha256()
        for f in sorted((d / "tests/reference").glob("*.xml")):
            h.update(f.name.encode()); h.update(f.read_bytes())
        assert re.search(r'reference_sha256 = "(\w+)"', (d / "task.toml").read_text()).group(1) == h.hexdigest()[:16]


def test_vendored_scorers_are_current():
    paper = (ROOT / "src/eval/judge_geos.py").read_text()
    fixed = (ROOT / "src/eval/judge_geos_fixed.py").read_text()
    score = (BENCH / "siga_bench/verifier_score.py").read_text()
    assert paper != fixed
    for name in ALL:
        t = config.TASKS_DIR / config.task_id(name) / "tests"
        assert (t / "judge_geos_paper.py").read_text() == paper, name
        assert (t / "judge_geos_fixed.py").read_text() == fixed, name
        assert (t / "score.py").read_text() == score, name


@pytest.mark.parametrize("scorer", SCORERS)
@pytest.mark.parametrize("name", ALL)
def test_oracle_scores_one_and_failures_score_zero(name, scorer, tmp_path):
    from siga_bench.runner import verify
    d = config.task_dir(name)
    r = verify(d, d / "solution" / "inputs", tmp_path / "v1", scorer)
    assert r["reward"] > 0.999 and r["scorer"] == scorer
    (tmp_path / "empty").mkdir()
    r = verify(d, tmp_path / "empty", tmp_path / "v2", scorer)
    assert r["reward"] == 0.0 and r["failure"] == "no_xml"
    bad = tmp_path / "bad"; bad.mkdir(); (bad / "x.xml").write_text("<Problem><Mesh>")
    assert verify(d, bad, tmp_path / "v3", scorer)["reward"] == 0.0


def test_default_scorer_is_paper_and_env_switch(tmp_path):
    d = config.task_dir("ExampleMandel")
    base = [sys.executable, str(d / "tests/score.py"), "--reference", str(d / "tests/reference"),
            "--generated", str(d / "solution/inputs")]
    env = {k: v for k, v in os.environ.items() if k != "SIGA_SCORER"}
    out = subprocess.run(base + ["--out", str(tmp_path / "a")], env=env, capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["scorer"] == "paper"
    out = subprocess.run(base + ["--out", str(tmp_path / "b")], env=dict(env, SIGA_SCORER="fixed"),
                         capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["scorer"] == "fixed"
    out = subprocess.run(base + ["--out", str(tmp_path / "c"), "--scorer", "paper"],
                         env=dict(env, SIGA_SCORER="fixed"), capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["scorer"] == "paper"   # the flag wins over the env var


def test_scorers_differ_on_a_known_case(tmp_path):
    """Bug 4 of the audit: whitespace inside GEOS arrays. The paper scorer penalizes it."""
    from siga_bench.runner import verify
    d = config.task_dir("ExampleMandel")
    gen = tmp_path / "gen"
    shutil.copytree(d / "solution/inputs", gen)
    for f in gen.glob("*.xml"):
        f.write_text(f.read_text().replace("{ ", "{").replace(" }", "}"))
    paper = verify(d, gen, tmp_path / "p", "paper")["reward"]
    fixed = verify(d, gen, tmp_path / "f", "fixed")["reward"]
    assert fixed > 0.999 and paper < fixed


def test_block_lists_cover_the_reference():
    for name in ALL:
        d = config.task_dir(name)
        bl = (d / "environment/blocked_files.txt").read_text().split()
        refs = {p.name.lower() for p in (d / "tests/reference").glob("*.xml")}
        assert refs <= {Path(b).name.lower() for b in bl}, name
        assert all(not b.startswith("/") and ".." not in b for b in bl), name
    pkn = (config.task_dir("pknViscosityDominated") / "environment/blocked_files.txt").read_text().split()
    assert "inputFiles/hydraulicFracturing/pknViscosityDominated_poroelastic_benchmark.xml" in pkn
    hf = (config.task_dir("TutorialHydraulicFractureWithAdvancedXML") / "environment/blocked_files.txt").read_text()
    assert len(hf.split()) < 20, "stray hydraulicFracturing/ subdir of the GT must not drive the block list"


def test_filtered_tree_drops_vcs_blocked_and_escaping_links(tmp_path):
    from siga_bench import geostree
    src = tmp_path / "geos"
    (src / ".git").mkdir(parents=True); (src / ".git" / "HEAD").write_text("ref")
    (src / "inputFiles/poro").mkdir(parents=True)
    (src / "inputFiles/poro/answer.xml").write_text("<Problem/>")
    (src / "inputFiles/poro/sibling.xml").write_text("<Problem/>")
    (tmp_path / "secret.txt").write_text("host file")
    (src / "inputFiles/poro/link").symlink_to(tmp_path / "secret.txt")
    (src / "inputFiles/poro/inner").symlink_to("sibling.xml")
    dest = tmp_path / "out"
    geostree.build_filtered_tree(src, ["inputFiles/poro/answer.xml"], dest)
    names = {str(p.relative_to(dest)) for p in dest.rglob("*")}
    assert "inputFiles/poro/sibling.xml" in names and "inputFiles/poro/inner" in names
    assert not {".git", "inputFiles/poro/answer.xml", "inputFiles/poro/link"} & names
    assert (src / "inputFiles/poro/answer.xml").exists()   # the source tree is never modified


@pytest.mark.skipif(not HAVE_GEOS, reason="needs GEOS (set SIGA_GEOS_SRC)")
def test_filtered_tree_has_no_vcs_or_reference(tmp_path, monkeypatch):
    from siga_bench import geostree
    monkeypatch.setattr(config, "CACHE", tmp_path / "cache")
    d = config.task_dir("ExampleMandel")
    tree = geostree.filtered_tree(d)
    assert not any(p.name in {".git", ".hg", ".svn"} for p in tree.rglob(".*"))
    refs = {p.name for p in (d / "tests/reference").glob("*.xml")}
    assert not [p for p in tree.rglob("*.xml") if p.name in refs]


@pytest.mark.skipif(not HAVE_GEOS, reason="needs GEOS (set SIGA_GEOS_SRC)")
def test_leakscan_finds_no_blocked_near_copy():
    from siga_bench import leakscan
    idx = leakscan.index_tree(config.GEOS_SRC)
    r = leakscan.scan_task("pknViscosityDominated", idx)
    assert all("pknViscosityDominated_poroelastic" not in h["path"] for h in r["top"])


def test_missing_host_paths_fail_with_a_message(monkeypatch):
    monkeypatch.setattr(config, "GEOS_SRC", None)
    with pytest.raises(config.ConfigError, match="SIGA_GEOS_SRC"):
        from siga_bench import geostree
        geostree.filtered_tree(config.task_dir("ExampleMandel"))


def test_proxy_allowlist():
    allow = ["chatgpt.com", "openai.com"]
    assert host_allowed("chatgpt.com", allow) and host_allowed("api.openai.com", allow)
    for h in ("github.com", "raw.githubusercontent.com", "evilchatgpt.com", "openai.com.evil.org", "pypi.org"):
        assert not host_allowed(h, allow), h


def test_gate_usage_parser_and_https_only():
    from siga_bench.net import llm_gate
    sse = (b'data: {"choices":[]}\n\ndata: {"usage":{"prompt_tokens":10,"completion_tokens":2,"cost":0.001}}\n\n'
           b"data: [DONE]\n")
    assert llm_gate._find_usage(sse) == {"prompt_tokens": 10, "completion_tokens": 2, "cost": 0.001}
    with pytest.raises(AssertionError):
        llm_gate.Gate("m", 1.0, "/dev/null", "http://example.com/v1", "k")


def test_secret_env_values_are_redacted_in_logged_argv():
    from siga_bench.runner import _redact
    argv = ["bwrap", "--setenv", "ANTHROPIC_AUTH_TOKEN", "sekrit", "--setenv", "PATH", "/usr/bin"]
    out = _redact(argv)
    assert "sekrit" not in out and "/usr/bin" in out


def _ctx(tmp_path, agent_dir_files: dict):
    from siga_bench.adapters.base import RunContext
    ctx = RunContext(task="T", task_dir=tmp_path, model="m", seed=1, out=tmp_path, prompt="p", timeout_s=1)
    ctx.agent_dir.mkdir(parents=True, exist_ok=True)
    for k, v in agent_dir_files.items():
        (ctx.agent_dir / k).write_text(v)
    return ctx


def test_pi_metrics_parse(tmp_path):
    from siga_bench.adapters.pi import PiAdapter
    msg = {"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
           "usage": {"input": 100, "cacheRead": 50, "output": 20, "reasoning": 5},
           "content": [{"type": "thinking"}, {"type": "toolCall", "name": "read",
                       "arguments": {"path": "/geos_lib/inputFiles/poromechanics/x.xml"}},
                       {"type": "toolCall", "name": "bash", "arguments": {"command": "ls /geos_lib"}}]}}
    user = {"type": "message_end", "message": {"role": "user", "content": []}}
    gate = [{"id": 1, "status": 200, "cost": 0.01}, {"id": 2, "status": 200, "cost": 0.02}]
    ctx = _ctx(tmp_path, {"events.jsonl": "\n".join(json.dumps(x) for x in (user, msg, msg)),
                          "gate_usage.jsonl": "\n".join(json.dumps(x) for x in gate)})
    m = PiAdapter().collect(ctx)
    assert (m["turns"], m["tool_calls"], m["tokens_in"], m["tokens_cached_in"]) == (2, 4, 300, 100)
    assert (m["tokens_out"], m["tokens_reasoning"], m["usd"], m["exit_reason"]) == (40, 10, 0.03, "stop")
    assert len(m["commands"]) == 4


def test_codex_metrics_parse(tmp_path, monkeypatch):
    from siga_bench.adapters.codex import CodexAdapter
    ctx = _ctx(tmp_path, {})
    sess = ctx.home / ".codex/sessions/2026/11/03"; sess.mkdir(parents=True)
    rows = [
        {"type": "token_usage_record", "payload": {"response_id": "r1", "usage": {
            "input_tokens": 1000, "cached_input_tokens": 600, "output_tokens": 50, "reasoning_output_tokens": 30}}},
        {"type": "token_usage_record", "payload": {"response_id": "r1", "usage": {"input_tokens": 999}}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec",
            "input": "await tools.exec_command({cmd:'git log --all'})"}},
        {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "CommandExecution",
            "command": ["/bin/bash", "-lc", "cat /geos_lib/README.md"]}}},
        {"type": "event_msg", "payload": {"type": "task_complete"}},
    ]
    (sess / "rollout-x.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setenv("SIGA_PRICE_M", "1.0,0.1,10.0")
    m = CodexAdapter().collect(ctx)
    assert (m["turns"], m["tool_calls"], m["commands_executed"]) == (1, 1, 1)
    assert (m["tokens_in"], m["tokens_cached_in"], m["tokens_out"], m["tokens_reasoning"]) == (1000, 600, 50, 30)
    assert m["exit_reason"] == "completed"
    assert m["usd"] == round((400 * 1.0 + 600 * 0.1 + 50 * 10.0) / 1e6, 6)
    from siga_bench.runner import assemble
    out = assemble(ctx, "codex", m, {"reward": 0.5, "scorer": "paper"}, 0, False, 1.0)
    assert out["score"] == 0.5 and out["scorer"] == "paper"
    assert out["n_suspicious_commands"] == 1 and "git log" in out["suspicious_commands"][0]


def test_claude_code_metrics_parse(tmp_path):
    from siga_bench.adapters.claude_code import ClaudeCodeAdapter, DISALLOWED
    assert {"Skill", "AskUserQuestion", "WebFetch", "WebSearch", "Task"} <= set(DISALLOWED)
    ev = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"p": 1}}]}},
          {"type": "assistant", "message": {"content": [{"type": "text", "text": "done"}]}},
          {"type": "result", "subtype": "success", "total_cost_usd": 0.02,
           "usage": {"input_tokens": 10, "cache_read_input_tokens": 90, "cache_creation_input_tokens": 5,
                     "output_tokens": 7}}]
    ctx = _ctx(tmp_path, {"events.jsonl": "\n".join(json.dumps(x) for x in ev)})
    m = ClaudeCodeAdapter().collect(ctx)
    assert (m["turns"], m["tool_calls"], m["tokens_in"], m["tokens_cached_in"], m["tokens_out"]) == (2, 1, 105, 90, 7)
    assert (m["usd"], m["exit_reason"]) == (0.02, "success")


def test_adapter_keys_come_from_env(tmp_path, monkeypatch):
    from siga_bench.adapters.base import api_key
    monkeypatch.delenv("SIGA_TEST_KEY", raising=False)
    monkeypatch.delenv("SIGA_ENV_FILE", raising=False)
    assert api_key("SIGA_TEST_KEY") == ""
    (tmp_path / ".env").write_text("export SIGA_TEST_KEY='abc'\n")
    monkeypatch.setenv("SIGA_ENV_FILE", str(tmp_path / ".env"))
    assert api_key("SIGA_TEST_KEY") == "abc"
    monkeypatch.setenv("SIGA_TEST_KEY", "fromenv")
    assert api_key("SIGA_TEST_KEY") == "fromenv"


def test_cli_without_host_config(tmp_path):
    cli = [str(BENCH / "bin" / "siga-bench")]
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIGA_")}
    env["SIGA_PYTHON"] = sys.executable
    out = subprocess.run(cli + ["tasks", "--split", "val"], env=env, capture_output=True, text=True, check=True)
    assert len(out.stdout.splitlines()) == 17
    out = subprocess.run(cli + ["oracle", "--task", "ExampleMandel", "--out", str(tmp_path / "o")],
                         env=env, capture_output=True, text=True)
    assert out.returncode == 0 and json.loads(out.stdout)["reward"] == 1.0
    out = subprocess.run(cli + ["run", "--agent", "pi", "--model", "m", "--task", "ExampleMandel",
                                "--out", str(tmp_path / "r"), "--dry-run"], env=env, capture_output=True, text=True)
    assert out.returncode == 2 and "SIGA_GEOS_SRC" in out.stderr


@pytest.mark.skipif(not HAVE_SANDBOX, reason="needs bwrap + SIGA_ROOTFS + SIGA_GEOS_SRC")
def test_leak_probe_codex_sandbox(tmp_path):
    """The leak probe must come back clean inside the real Codex sandbox (no API calls)."""
    if config.CODEX_PKG is None or not config.CODEX_PKG.exists() or not config.CODEX_AUTH.exists():
        pytest.skip("codex not installed (SIGA_CODEX_PKG, SIGA_CODEX_AUTH)")
    from siga_bench.probe.probe import probe
    s = probe("codex", "ExampleMandel", tmp_path / "probe", model="gpt-6-luna")
    assert s["verdict"] == "PASS", s["fails"]
    assert s["n_checks"] >= 20


@pytest.mark.skipif(not HAVE_SANDBOX, reason="needs bwrap + SIGA_ROOTFS + SIGA_GEOS_SRC")
@pytest.mark.parametrize("cell", ["S+X+M", "SE"])
def test_leak_probe_siga_cell_sandbox(tmp_path, cell, monkeypatch):
    """A SIGA cell's sandbox (adapter dir at /plugins/siga) must pass the leak probe (no API calls)."""
    if not (config.ROOTFS / "opt/siga/venv").is_dir():
        pytest.skip("SIGA_ROOTFS has no /opt/siga/venv (build it from sandbox/Dockerfile)")
    monkeypatch.setenv("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY") or "dummy-not-used")
    from siga_bench.probe.probe import probe
    s = probe("siga", "ExampleMandel", tmp_path / "probe", model="m", options={"cell": cell})
    assert s["verdict"] == "PASS", s["fails"]
    assert {c["check"] for c in json.loads((tmp_path / "probe/probe_result.json").read_text())["checks"]
            if "check" in c} >= {"benchmark_files", "reference_copies", "reference_lines", "mounts"}


def test_sock_dir_short_for_long_run_dirs(tmp_path):
    from siga_bench.adapters.base import RunContext
    long_out = tmp_path / ("x" * 60) / "advancedexamplecasedcontactthermoelasticwellbore" / "1"
    ctx = RunContext(task="t", task_dir=tmp_path, model="m", seed=1, out=long_out, prompt="p", timeout_s=1)
    sock = ctx.sock_dir / "proxy.sock"
    assert len(str(sock)) < 100
    assert ctx.sock_dir == ctx.sock_dir  # deterministic per run dir
    assert ctx.sock_dir.is_dir() and (ctx.sock_dir.stat().st_mode & 0o777) == 0o700
    shutil.rmtree(ctx.sock_dir)
