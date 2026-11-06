#!/usr/bin/env python3
"""Host-side model gate for sandboxed agent runs.

Listens on a UNIX socket that is bind-mounted into the sandbox (the sandbox has
its own empty network namespace). Accepts only

    POST /api/v1/chat/completions   with "model" == the allowed model

and forwards it over TLS to an OpenAI-compatible API (default OpenRouter),
adding the API key on the host side. The key never enters the sandbox.
Before forwarding it:
  - rejects any other path, method or model (403);
  - strips request fields that would give the agent web access through the
    API (plugins, web_search_options, ...);
  - asks the upstream to report usage/cost for the request;
  - refuses new requests once the run's spend reaches --cap-usd (402).

Every request is logged as one JSON line to --log (status, tokens, cost);
the key and the prompt text are never logged.

    OPENROUTER_API_KEY=... python3 llm_gate.py --socket /path/llm.sock --model MODEL \
        --cap-usd 3 --log usage.jsonl
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socketserver
import ssl
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

STRIP_FIELDS = ("plugins", "web_search_options", "tools_server", "search_parameters")

class Gate:
    def __init__(self, model: str, cap: float, log_path: str, base_url: str, key: str, seed=None,
                 price_in: float = 0.14, price_out: float = 0.28):
        self.model = model
        self.seed = seed
        self.cap = cap
        self.log_path = log_path
        u = urlparse(base_url)
        assert u.scheme == "https", "upstream must be https"
        self.host = u.hostname
        self.port = u.port or 443
        self.prefix = u.path.rstrip("/")  # e.g. /api/v1
        self.key = key
        self.price_in, self.price_out = price_in, price_out  # $ per million tokens, when the upstream reports no cost
        self.timeout = 600.0
        self.spent = 0.0
        self.n = 0
        self.lock = threading.Lock()
        self.ctx = ssl.create_default_context()

    def connect(self, timeout: float):
        return http.client.HTTPSConnection(self.host, self.port, context=self.ctx, timeout=timeout)

    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "HTTP-Referer": "https://github.com/matt-seb-ho/siga",
             "X-Title": "siga-bench"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    def price(self, usage: dict) -> float:
        return (usage.get("prompt_tokens", 0) * self.price_in + usage.get("completion_tokens", 0) * self.price_out) / 1e6

    def log(self, rec: dict) -> None:
        rec["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock, open(self.log_path, "a") as f:
            f.write(json.dumps(rec) + "\n")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    gate: Gate  # set on the class

    def log_message(self, *a):  # silence default stderr logging
        pass

    def _deny(self, code: int, msg: str) -> None:
        body = json.dumps({"error": {"message": msg, "code": code}}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.gate.log({"status": code, "deny": msg, "path": self.path})

    def do_GET(self):
        self._deny(403, "only POST /api/v1/chat/completions is allowed")

    do_PUT = do_DELETE = do_PATCH = do_HEAD = do_GET

    def do_POST(self):
        g = self.gate
        path = urlparse(self.path).path
        if path.rstrip("/") not in ("/api/v1/chat/completions", "/v1/chat/completions", "/chat/completions"):
            return self._deny(403, f"path not allowed: {path}")
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        try:
            req = json.loads(raw)
        except Exception:
            return self._deny(400, "body is not JSON")
        if req.get("model") != g.model:
            return self._deny(403, f"model not allowed: {req.get('model')!r}")
        with g.lock:
            if g.spent >= g.cap:
                over = True
            else:
                over = False
                g.n += 1
                rid = g.n
        if over:
            return self._deny(402, f"run budget exhausted (${g.spent:.4f} >= ${g.cap})")
        stripped = [k for k in STRIP_FIELDS if req.pop(k, None) is not None]
        req["usage"] = {"include": True}
        if g.seed is not None:
            req["seed"] = g.seed
        if req.get("stream"):
            so = req.setdefault("stream_options", {})
            so["include_usage"] = True
        body = json.dumps(req).encode()

        t0 = time.time()
        conn = g.connect(g.timeout)
        try:
            conn.request("POST", g.prefix + "/chat/completions", body=body,
                         headers=dict(g.headers(), Accept=self.headers.get("Accept", "*/*")))
            resp = conn.getresponse()
        except Exception as e:  # upstream unreachable
            conn.close()
            return self._deny(502, f"upstream error: {type(e).__name__}")

        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() in ("transfer-encoding", "content-length", "connection", "content-encoding",
                             "set-cookie", "strict-transport-security"):
                continue
            self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()

        usage = None
        tail = b""
        nbytes = 0
        try:
            while True:
                chunk = resp.read1(65536) if hasattr(resp, "read1") else resp.read(65536)
                if not chunk:
                    break
                nbytes += len(chunk)
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
                tail = (tail + chunk)[-65536:]
                if b'"usage"' in chunk or b'"cost"' in chunk:
                    u = _find_usage(tail)
                    if u:
                        usage = u
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            conn.close()
        if usage is None:
            usage = _find_usage(tail)
        cost = float((usage or {}).get("cost") or 0.0)
        if usage and not cost:
            # fallback when the upstream reports no cost: price the tokens (--price-in/--price-out)
            cost = g.price(usage)
        with g.lock:
            g.spent += cost
            spent = g.spent
        g.log({"id": rid, "status": resp.status, "secs": round(time.time() - t0, 2), "bytes": nbytes,
               "prompt_tokens": (usage or {}).get("prompt_tokens"),
               "completion_tokens": (usage or {}).get("completion_tokens"),
               "cost": round(cost, 6), "spent": round(spent, 6), "stripped": stripped,
               "usage_seen": usage is not None})


def _find_usage(buf: bytes):
    """Return the last usage object in an SSE or JSON body, if any."""
    txt = buf.decode("utf-8", "replace")
    best = None
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if '"usage"' not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        u = obj.get("usage")
        if isinstance(u, dict) and u:
            best = u
    return best


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def get_request(self):
        req, _ = super().get_request()
        return req, ("sandbox", 0)  # BaseHTTPRequestHandler wants an address tuple


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--socket", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--seed", type=int, default=None, help="sampling seed added to every request")
    ap.add_argument("--base-url", default=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    help="upstream OpenAI-compatible base URL (https)")
    ap.add_argument("--price-in", type=float, default=0.14,
                    help="$/Mtok prompt, used only when the upstream reports no cost")
    ap.add_argument("--price-out", type=float, default=0.28,
                    help="$/Mtok completion, used only when the upstream reports no cost")
    ap.add_argument("--timeout", type=float, default=600, help="upstream request timeout, seconds")
    a = ap.parse_args()
    key = os.environ.pop("OPENROUTER_API_KEY", "")
    if not key:
        print("llm_gate: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2
    if os.path.exists(a.socket):
        os.unlink(a.socket)
    Handler.gate = Gate(a.model, a.cap_usd, a.log, a.base_url, key, a.seed, a.price_in, a.price_out)
    Handler.gate.timeout = a.timeout
    srv = Server(a.socket, Handler)
    os.chmod(a.socket, 0o600)
    print(f"llm_gate: listening on {a.socket} for {a.model}, cap ${a.cap_usd}", file=sys.stderr, flush=True)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()
        try:
            os.unlink(a.socket)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
