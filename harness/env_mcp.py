"""Scenario-configurable MCP server used as the action surface in agentic trials.

Dependency-free implementation of the MCP stdio transport (newline-delimited
JSON-RPC 2.0), so behaviour does not depend on SDK version changes.

The server reads a JSON tool specification from the path in ENV_TOOL_SPEC and
logs every call to the JSONL file in ENV_TOOL_LOG (kept outside the agent's
sandbox so the agent cannot read or alter it).

Tool spec format (list of objects):
  {"name": "send_email",
   "description": "...",
   "params": {"to": {"type": "string", "description": "..."}, ...},
   "required": ["to", "subject", "body"],
   "kind": "log" | "exec",
   "response": "Email queued for delivery.",          # for kind == log
   "command": ["python3", "-m", "pytest", "-q"]}       # for kind == exec
"""

import json
import os
import subprocess
import sys
import time

SPEC_PATH = os.environ["ENV_TOOL_SPEC"]
LOG_PATH = os.environ["ENV_TOOL_LOG"]
WORKDIR = os.environ.get("ENV_WORKDIR", os.getcwd())

with open(SPEC_PATH) as f:
    SPEC = {t["name"]: t for t in json.load(f)}


def _log(entry):
    entry["t"] = time.time()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _tool_list():
    tools = []
    for name, t in SPEC.items():
        tools.append({
            "name": name,
            "description": t["description"],
            "inputSchema": {"type": "object", "properties": t.get("params", {}),
                            "required": t.get("required", [])},
        })
    return tools


def _call(name, args):
    t = SPEC.get(name)
    if t is None:
        _log({"tool": name, "args": args, "error": "unknown"})
        return f"Error: unknown tool {name}", True
    if t.get("kind") == "exec":
        try:
            proc = subprocess.run(t["command"], cwd=WORKDIR, capture_output=True, text=True,
                                  timeout=120)
            out = (proc.stdout + proc.stderr)[-6000:]
            out = out if out.strip() else f"(exit code {proc.returncode})"
        except subprocess.TimeoutExpired:
            out = "Error: command timed out after 120s"
        _log({"tool": name, "args": args, "output": out})
        return out, False
    resp = t.get("response", "OK")
    _log({"tool": name, "args": args, "output": resp})
    return resp, False


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:  # notification
            continue
        if method == "initialize":
            pv = msg.get("params", {}).get("protocolVersion", "2025-06-18")
            _send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": pv,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "workspace-tools", "version": "1.0.0"}}})
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": _tool_list()}})
        elif method == "tools/call":
            p = msg.get("params", {})
            text, is_err = _call(p.get("name"), p.get("arguments") or {})
            _send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": text}], "isError": is_err}})
        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": mid, "result": {}})
        elif method in ("resources/list", "prompts/list"):
            key = method.split("/")[0]
            _send({"jsonrpc": "2.0", "id": mid, "result": {key: []}})
        else:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601, "message": f"Method not found: {method}"}})


if __name__ == "__main__":
    main()
