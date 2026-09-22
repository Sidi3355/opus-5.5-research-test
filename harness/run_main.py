"""Main experiment (E1 + E2): every task x condition x model x trial, with an
in-session follow-up probe after trials graded as hacks.

Resumable: completed trial records are skipped. Stops submitting new trials once
cumulative cost exceeds --budget.

Usage: python3 harness/run_main.py --workers 12 --budget 350
"""

import argparse
import glob
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coding import CONDITIONS, build_condition, grade, make_followup_fn, validate_task  # noqa: E402
from runner import run_trial  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "main"
TRIALS = {"haiku-4.5": 3, "sonnet-4.5": 2, "opus-4.5": 2, "sonnet-5": 2, "opus-5.5": 3, "fable-5.1": 2}

lock = threading.Lock()
state = {"cost": 0.0, "done": 0, "hacks": 0, "errors": 0}


def load_tasks():
    tasks = []
    for p in sorted(glob.glob(str(REPO / "tasks" / "*" / "task.json"))):
        if "/pilot/" in p:
            continue
        t = json.load(open(p))
        if t.get("excluded"):
            continue
        tasks.append(t)
    return tasks


def out_path(task, cond, model, idx):
    return OUT / model / f"{task['task_id']}__{cond}__{idx}.json"


def is_complete(p):
    if not p.exists():
        return False
    try:
        r = json.load(open(p))
    except Exception:
        return False
    return not r.get("errors") and r.get("served_ok")


def cleanup_sessions(record):
    # Session transcripts are only needed during the trial (probe resumes).
    slug_dir = Path.home() / ".claude" / "projects"
    for d in slug_dir.glob(f"*{record['trial_uid']}*"):
        shutil.rmtree(d, ignore_errors=True)


def job(task, cond_name, model, idx, log):
    p = out_path(task, cond_name, model, idx)
    cond = build_condition(task, cond_name)
    rec = None
    for attempt in range(2):
        rec = run_trial(cond, model, idx, p, followup_fn=make_followup_fn(task))
        cleanup_sessions(rec)
        if not rec["errors"] and rec["served_ok"]:
            break
    g = grade(task, rec)
    with lock:
        state["cost"] += rec["cost_usd"]
        state["done"] += 1
        state["hacks"] += int(g["hack"])
        state["errors"] += int(bool(rec["errors"]) or not rec["served_ok"])
        line = (f"{time.strftime('%H:%M:%S')} done={state['done']} cost=${state['cost']:.2f} "
                f"hacks={state['hacks']} errors={state['errors']} | {model} {task['task_id']} {cond_name} "
                f"#{idx} hack={g['hack']} sc={g['special_cased']} mod={bool(g['protected_changed'])} "
                f"${rec['cost_usd']:.3f}")
        log.write(line + "\n")
        log.flush()
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--budget", type=float, default=350.0)
    ap.add_argument("--models", default=",".join(TRIALS))
    args = ap.parse_args()
    tasks = load_tasks()
    for t in tasks:
        v = validate_task(t)
        if not v["valid"]:
            raise SystemExit(f"invalid task {t['task_id']}: {v}")
    models = args.models.split(",")
    jobs = []
    # Interleave models and tasks so partial runs are balanced.
    max_n = max(TRIALS[m] for m in models)
    for idx in range(max_n):
        for t in tasks:
            for c in CONDITIONS:
                for m in models:
                    if idx < TRIALS[m] and not is_complete(out_path(t, c, m, idx)):
                        jobs.append((t, c, m, idx))
    OUT.mkdir(parents=True, exist_ok=True)
    # Count cost already spent on completed trials.
    for f in glob.glob(str(OUT / "*" / "*.json")):
        try:
            state["cost"] += json.load(open(f)).get("cost_usd", 0.0)
        except Exception:
            pass
    print(f"{len(tasks)} tasks, {len(jobs)} trials to run, prior cost ${state['cost']:.2f}", flush=True)
    with open(OUT / "progress.log", "a") as log, ThreadPoolExecutor(args.workers) as ex:
        futs = []
        for j in jobs:
            while True:
                with lock:
                    over = state["cost"] > args.budget
                    inflight = sum(1 for f in futs if not f.done())
                if over:
                    break
                if inflight < args.workers * 2:
                    futs.append(ex.submit(job, *j, log))
                    break
                time.sleep(2)
            if over:
                log.write(f"BUDGET REACHED at ${state['cost']:.2f}; not submitting further trials\n")
                break
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:  # keep going; record the failure
                with open(OUT / "progress.log", "a") as lg:
                    lg.write(f"EXCEPTION {e!r}\n")
    print(f"finished: {state}", flush=True)


if __name__ == "__main__":
    main()
