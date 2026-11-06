#!/usr/bin/env python3
"""Host-side HTTP CONNECT proxy on a UNIX socket, with a host allowlist.

The agent sandbox has its own empty network namespace. For agents that must
reach a fixed TLS endpoint themselves (Codex -> chatgpt.com), the sandbox's
relay (relay.py) pipes 127.0.0.1:8080 to this socket and the agent is given
HTTPS_PROXY=http://127.0.0.1:8080. Only `CONNECT host:443` to an allowlisted
host is honoured; everything else gets 403. Each decision is logged as one
JSON line (host, allowed, bytes) so a run's network use can be audited.

    python3 connect_proxy.py --socket /run/x.sock --allow chatgpt.com --allow auth.openai.com --log net.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time

_lock = threading.Lock()


def log(path: str | None, rec: dict) -> None:
    if not path:
        return
    rec["t"] = round(time.time(), 3)
    with _lock, open(path, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def host_allowed(host: str, allow: list[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == a or host.endswith("." + a) for a in allow)


def pipe(a: socket.socket, b: socket.socket, counter: list[int]) -> None:
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            counter[0] += len(d)
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle(c: socket.socket, allow: list[str], logpath: str | None) -> None:
    buf = b""
    try:
        while b"\r\n\r\n" not in buf and len(buf) < 16384:
            d = c.recv(4096)
            if not d:
                c.close()
                return
            buf += d
        head, _, rest = buf.partition(b"\r\n\r\n")
        line = head.split(b"\r\n", 1)[0].decode("latin-1")
        parts = line.split()
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            log(logpath, {"req": line[:200], "allowed": False, "why": "not CONNECT"})
            c.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            c.close()
            return
        host, _, port = parts[1].rpartition(":")
        host = host.strip("[]")
        if port != "443" or not host_allowed(host, allow):
            log(logpath, {"host": host, "port": port, "allowed": False})
            c.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            c.close()
            return
        u = socket.create_connection((host, 443), timeout=30)
        u.settimeout(None)
        c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        if rest:
            u.sendall(rest)
        up, down = [0], [0]
        t = threading.Thread(target=pipe, args=(c, u, up), daemon=True)
        t.start()
        pipe(u, c, down)
        t.join(timeout=5)
        log(logpath, {"host": host, "port": port, "allowed": True, "up": up[0], "down": down[0]})
    except OSError as e:
        log(logpath, {"error": str(e)[:200]})
        try:
            c.close()
        except OSError:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--socket", required=True)
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--log")
    a = ap.parse_args()
    if os.path.exists(a.socket):
        os.unlink(a.socket)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(a.socket)
    os.chmod(a.socket, 0o600)
    s.listen(64)
    while True:
        c, _ = s.accept()
        threading.Thread(target=handle, args=(c, a.allow, a.log), daemon=True).start()


if __name__ == "__main__":
    main()
