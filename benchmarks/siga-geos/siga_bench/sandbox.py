"""bwrap sandbox for one agent run.

What the agent sees (everything else on the host is absent):
  /usr, /etc            the agent image userland (sandbox/Dockerfile), read-only
                        (Ubuntu 24.04: python3, node 22, xmllint, git, curl, ripgrep)
  /geos_lib             the task's filtered GEOS tree, read-only (no VCS dirs, no blocked files)
  /workspace            rw; the agent writes its deck to /workspace/inputs/
  /home/agent           rw; agent config and session logs
  /tmp                  fresh tmpfs
  /opt/...              read-only agent toolchains (node, pi, codex), the relay script
  /run/net/*.sock       the only way out: a UNIX socket to a host-side gate or proxy
The sandbox has its own network namespace (loopback only), pid/ipc/uts/user
namespaces, a cleared environment, and dies with its parent.
"""
from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path

from . import config

RELAY = Path(__file__).parent / "net" / "relay.py"
RELAY_PORT = 8080


@dataclass
class SandboxSpec:
    geos_lib: Path
    workspace: Path
    home: Path
    sock_dir: Path
    ro_binds: list[tuple[Path, str]] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    path_prefix: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)


def bwrap_argv(spec: SandboxSpec, rootfs: Path = None) -> list[str]:
    rootfs = rootfs or config.require("SIGA_ROOTFS", config.ROOTFS, "an unpacked rootfs of sandbox/Dockerfile")
    a = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--hostname", "sandbox",
         "--ro-bind", str(rootfs / "usr"), "/usr",
         "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
         "--symlink", "usr/lib64", "/lib64", "--symlink", "usr/sbin", "/sbin",
         "--ro-bind", str(rootfs / "etc"), "/etc",
         "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
         "--ro-bind", str(spec.geos_lib), "/geos_lib",
         "--bind", str(spec.workspace), "/workspace",
         "--bind", str(spec.home), "/home/agent",
         "--ro-bind", str(spec.sock_dir), "/run/net",
         "--ro-bind", str(RELAY), "/opt/relay.py"]
    for src, dst in spec.ro_binds:
        a += ["--ro-bind", str(src), dst]
    path = ":".join(spec.path_prefix + ["/usr/local/bin", "/usr/bin", "/bin"])
    a += ["--chdir", "/workspace", "--clearenv",
          "--setenv", "HOME", "/home/agent", "--setenv", "USER", "agent",
          "--setenv", "LANG", "C.UTF-8", "--setenv", "TERM", "dumb", "--setenv", "TMPDIR", "/tmp",
          "--setenv", "PATH", path]
    for k, v in spec.env.items():
        a += ["--setenv", k, v]
    a += spec.extra_args
    return a


def with_relay(sock_name: str, inner: list[str]) -> list[str]:
    """bash -c wrapper: start the in-sandbox relay to /run/net/<sock>, wait for it, exec inner."""
    start = (f"python3 /opt/relay.py {RELAY_PORT} /run/net/{sock_name} & "
             f"for i in $(seq 50); do (exec 3<>/dev/tcp/127.0.0.1/{RELAY_PORT}) 2>/dev/null && break; sleep 0.1; done; ")
    return ["bash", "-c", start + 'exec "$@"', "_"] + inner


def render(argv: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in argv)
