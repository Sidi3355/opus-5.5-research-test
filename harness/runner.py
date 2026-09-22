"""Trial runner: executes one scenario condition against one subject model.

Two modes:
  * agentic: the subject gets Claude Code file tools (Read, Write, Edit, Glob,
    Grep) confined to a fresh sandbox directory, plus scenario-specific action
    tools served by env_mcp.py. Every tool call is logged.
  * chat: no tools; one or more user turns (later turns resume the session so
    the subject's own earlier replies are part of the context).

Every trial record stores the model that actually served the request (from the
CLI's modelUsage), so silent aliasing can be detected and filtered.
"""

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
REPO = HARNESS.parent
META_ROOT = Path("/var/lib/trialmeta")
SANDBOX_ROOT = Path("/workspace")

MODELS = {
    "haiku-4.5": "claude-haiku-4-5-20251001",
    "sonnet-4.5": "claude-sonnet-4-5",
    "opus-4.5": "claude-opus-4-5",
    "sonnet-5": "claude-sonnet-5",
    "opus-5.5": "claude-opus-5-5",
    "fable-5.1": "claude-fable-5-1",
}
CANONICAL = {
    "haiku-4.5": "claude-haiku-4-5",
    "sonnet-4.5": "claude-sonnet-4-5",
    "opus-4.5": "claude-opus-4-5",
    "sonnet-5": "claude-sonnet-5",
    "opus-5.5": "claude-opus-5-5",
    "fable-5.1": "claude-fable-5-1",
}

FILE_TOOLS = "Read,Write,Edit,Glob,Grep"


def _parse_stream(stdout):
    events, texts, tool_calls, tool_results = [], [], [], []
    result = None
    init = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            init = {"tools": d.get("tools"), "mcp_servers": d.get("mcp_servers"), "model": d.get("model")}
        elif t == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "text":
                    texts.append(c["text"])
                elif c.get("type") == "tool_use":
                    tool_calls.append({"id": c.get("id"), "name": c.get("name"), "input": c.get("input")})
        elif t == "user":
            content = d.get("message", {}).get("content", [])
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        out = c.get("content")
                        if isinstance(out, list):
                            out = "\n".join(x.get("text", "") for x in out if isinstance(x, dict))
                        tool_results.append({"id": c.get("tool_use_id"), "output": str(out)[:4000],
                                             "is_error": c.get("is_error", False)})
        elif t == "result":
            result = d
    return texts, tool_calls, tool_results, result, init


def served_ok(model_key, served):
    """True iff every model that served a request is the requested model."""
    served = list(served)
    return bool(served) and all(s.startswith(CANONICAL[model_key]) for s in served)


def _served_models(result):
    if not result:
        return []
    return sorted((result.get("modelUsage") or {}).keys())


def _cli(prompt, model_id, system_prompt, cwd, tools, mcp_cfg=None, allowed=None,
         resume=None, persist=False, effort=None, timeout=900, budget=None):
    cmd = ["claude", "-p", prompt, "--model", model_id, "--system-prompt", system_prompt,
           "--output-format", "stream-json", "--verbose", "--restricted",
           "--disable-slash-commands", "--setting-sources", ""]
    cmd += ["--tools", tools]
    if tools:
        cmd += ["--permission-mode", "acceptEdits"]
    if mcp_cfg:
        cmd += ["--mcp-config", str(mcp_cfg), "--strict-mcp-config"]
    else:
        cmd += ["--strict-mcp-config"]
    if allowed:
        cmd += ["--allowedTools", ",".join(allowed)]
    if resume:
        cmd += ["--resume", resume]
    if not persist:
        cmd += ["--no-session-persistence"]
    if effort:
        cmd += ["--effort", effort]
    if budget:
        cmd += ["--max-budget-usd", str(budget)]
    env = dict(os.environ)
    env["MCP_CONNECTION_NONBLOCKING"] = "false"
    env["ENABLE_TOOL_SEARCH"] = "false"
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env,
                              stdin=subprocess.DEVNULL)
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr, rc = "TIMEOUT", -9
    return stdout, stderr, rc, time.time() - t0


def _snapshot(root):
    snap = {}
    for p in Path(root).rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(root))
            try:
                snap[rel] = p.read_text()
            except UnicodeDecodeError:
                snap[rel] = "<binary>"
    return snap


def run_trial(cond, model_key, trial_idx, out_path, effort=None, keep_sandbox=False):
    """Run a single trial of a scenario condition and write a JSON record."""
    model_id = MODELS[model_key]
    tid = uuid.uuid4().hex[:6]
    record = {"cond_id": cond["cond_id"], "scenario_id": cond["scenario_id"], "family": cond["family"],
              "condition": cond["condition"], "model_key": model_key, "model_id": model_id,
              "trial_idx": trial_idx, "trial_uid": tid, "effort": effort, "started": time.time()}
    mode = cond.get("mode", "chat")
    slug = cond.get("workspace_slug", "work")
    sandbox = SANDBOX_ROOT / f"{slug}-{tid}"
    meta = META_ROOT / tid
    sandbox.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    for rel, content in (cond.get("files") or {}).items():
        p = sandbox / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    initial = _snapshot(sandbox)

    mcp_cfg, allowed = None, None
    tools = FILE_TOOLS if mode == "agentic" else ""
    if cond.get("tools"):
        spec_path = meta / "tools.json"
        spec_path.write_text(json.dumps(cond["tools"]))
        log_path = meta / "tool_log.jsonl"
        log_path.touch()
        cfg = {"mcpServers": {"tools": {
            "command": "python3", "args": [str(HARNESS / "env_mcp.py")],
            "env": {"ENV_TOOL_SPEC": str(spec_path), "ENV_TOOL_LOG": str(log_path),
                    "ENV_WORKDIR": str(sandbox)}}}}
        mcp_cfg = meta / "mcp.json"
        mcp_cfg.write_text(json.dumps(cfg))
        allowed = [f"mcp__tools__{t['name']}" for t in cond["tools"]]

    turns = cond["turns"]
    transcript = []
    session_id = None
    total_cost = 0.0
    served = set()
    errors = []
    for i, user_msg in enumerate(turns):
        persist = len(turns) > 1
        stdout, stderr, rc, dt = _cli(user_msg, model_id, cond["system_prompt"], sandbox, tools,
                                      mcp_cfg=mcp_cfg, allowed=allowed, resume=session_id,
                                      persist=persist, effort=effort,
                                      budget=cond.get("budget_usd", 3.0))
        texts, calls, results, result, init = _parse_stream(stdout)
        if allowed:
            missing = [a for a in allowed if not init or a not in (init.get("tools") or [])]
            if missing:
                errors.append({"turn": i, "missing_tools": missing})
        if result is None or result.get("is_error"):
            errors.append({"turn": i, "rc": rc, "stderr": stderr[-2000:],
                           "result": (result or {}).get("result") if result else None,
                           "subtype": (result or {}).get("subtype") if result else None})
        if result:
            session_id = result.get("session_id")
            total_cost += result.get("total_cost_usd") or 0.0
            served.update(_served_models(result))
        transcript.append({"user": user_msg, "assistant_texts": texts, "tool_calls": calls,
                           "tool_results": results, "final": (result or {}).get("result"),
                           "num_turns": (result or {}).get("num_turns"), "duration_s": dt,
                           "stop_reason": (result or {}).get("stop_reason"),
                           "terminal_reason": (result or {}).get("terminal_reason"),
                           "init": init})
    final = _snapshot(sandbox)
    diffs = {k: {"before": initial.get(k), "after": v} for k, v in final.items() if initial.get(k) != v}
    for k in initial:
        if k not in final:
            diffs[k] = {"before": initial[k], "after": None}
    tool_log = []
    lp = meta / "tool_log.jsonl"
    if lp.exists():
        tool_log = [json.loads(x) for x in lp.read_text().splitlines() if x.strip()]
    record.update({"transcript": transcript, "file_diffs": diffs, "tool_log": tool_log,
                   "cost_usd": total_cost, "served_models": sorted(served),
                   "served_ok": served_ok(model_key, served),
                   "errors": errors, "finished": time.time()})
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1))
    if not keep_sandbox:
        shutil.rmtree(sandbox, ignore_errors=True)
        shutil.rmtree(meta, ignore_errors=True)
    return record
