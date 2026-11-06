"""The adapter contract.

An adapter turns (task instruction, model) into one sandboxed agent
process and turns its trajectory back into common metrics. The runner owns
everything else: the filtered GEOS tree, the sandbox, timeouts, verification,
metrics.json. An adapter implements five methods:

  setup(ctx)            write agent config into ctx.home (the sandbox's /home/agent)
  services(ctx)         start host-side network services on ctx.sock_dir and return
                        the Popen handles (a model gate, or an allowlisting proxy).
                        The sandbox has no network; these sockets are the only way out.
  sandbox(ctx, spec)    add read-only binds / env / PATH entries to the SandboxSpec
  command(ctx)          argv to run inside the sandbox (the prompt is ctx.prompt)
  collect(ctx)          parse ctx.agent_dir after the run and return a dict with the
                        agent-specific metrics.json fields: tokens_in (all prompt tokens,
                        cached included), tokens_cached_in, tokens_out (completion tokens,
                        reasoning included), tokens_reasoning, usd, usd_basis, tool_calls,
                        turns, exit_reason (optional), commands (list of command or
                        tool-argument strings, screened for leak-hunting)
  finalize(ctx)         optional cleanup after collect (e.g. credential copy-back)

Turns and tool calls follow the SIGA paper's efficiency table: a turn is
one assistant message (one model response); a tool call is one tool-use block the
model emitted. Each adapter documents its mapping in its module docstring.
"""
from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..sandbox import SandboxSpec


@dataclass
class RunContext:
    task: str                 # SIGA task name, e.g. ExampleMandel
    task_dir: Path            # Harbor task dir
    model: str
    seed: int
    out: Path                 # run dir
    prompt: str
    timeout_s: int
    options: dict = field(default_factory=dict)   # adapter-specific (effort, thinking, cap_usd, ...)

    @property
    def workspace(self) -> Path:
        return self.out / "workspace"

    @property
    def home(self) -> Path:
        return self.out / "home"

    @property
    def sock_dir(self) -> Path:
        # UNIX socket paths are limited to 107 bytes; long run dirs (task names like
        # advancedexamplecasedcontactthermoelasticwellbore) overflow that. Use a short,
        # per-run-dir directory under /tmp instead of <out>/sock.
        import hashlib
        h = hashlib.sha256(str(self.out.resolve()).encode()).hexdigest()[:16]
        d = Path("/tmp") / f"siga-sock-{h}"
        d.mkdir(mode=0o700, exist_ok=True)
        st = os.lstat(d)
        if stat.S_ISLNK(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise RuntimeError(f"{d} exists but is not a private directory owned by this user")
        return d

    @property
    def agent_dir(self) -> Path:
        return self.out / "agent"


class Adapter:
    name = "base"

    def setup(self, ctx: RunContext) -> None:
        pass

    def services(self, ctx: RunContext) -> list[subprocess.Popen]:
        return []

    def sandbox(self, ctx: RunContext, spec: SandboxSpec) -> None:
        pass

    def command(self, ctx: RunContext) -> list[str]:
        raise NotImplementedError

    def collect(self, ctx: RunContext) -> dict:
        return {}

    def finalize(self, ctx: RunContext) -> None:
        pass


def start(cmd: list[str], log: Path, env: dict | None = None) -> subprocess.Popen:
    fh = open(log, "ab")
    return subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, start_new_session=True)


def wait_socket(path: Path, procs: list[subprocess.Popen], timeout: float = 10) -> None:
    import time
    t0 = time.time()
    while time.time() - t0 < timeout:
        if path.exists():
            return
        if any(p.poll() is not None for p in procs):
            break
        time.sleep(0.1)
    raise RuntimeError(f"service socket {path} did not appear")


def api_key(var: str) -> str:
    """The API key in environment variable `var`, else in the dotenv file $SIGA_ENV_FILE."""
    import os
    if os.environ.get(var):
        return os.environ[var]
    env_file = os.environ.get("SIGA_ENV_FILE")
    return load_env_file(Path(env_file)).get(var, "") if env_file else ""


def load_env_file(path: Path) -> dict[str, str]:
    env = {}
    if not path.exists():
        return env
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.replace("export ", "").strip()
        env[k] = v.strip().strip('"').strip("'")
    return env
