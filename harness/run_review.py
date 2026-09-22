"""E3: code-review experiment on special-cased trials.

Packets: every special-cased (tests untouched) trial whose primary-judge label
is fabricated_requirement, plus up to --n_other other special-cased trials as
an exploratory comparison. For each packet we write an honest minimal rewrite
of the agent's report, verify it with the report judge (manipulation check:
it must be coded "transparent"), and collect one review per reviewer model
for each description variant (original / honest / none).

Outputs data/graded/review.jsonl. Results are cached per call in data/review/.

Usage: python3 harness/run_review.py --workers 12
"""

import argparse
import copy
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coding import grade  # noqa: E402
from judge import code_report, final_report  # noqa: E402
from review import honest_rewrite, review  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "data" / "review"
REVIEWERS = ("opus-5.5", "sonnet-5", "haiku-4.5")
VARIANTS = ("original", "honest", "none")


def cached(path, fn):
    if path.exists():
        return json.load(open(path))
    res = fn()
    if res is not None and res.get("output") is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        json.dump(res, open(path, "w"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--n_other", type=int, default=40)
    ap.add_argument("--reviewers", default=",".join(REVIEWERS))
    ap.add_argument("--out", default="review.jsonl")
    ap.add_argument("--diff_only", action="store_true",
                    help="exploratory: reviewer sees request, description and diff, but not the repository")
    args = ap.parse_args()
    reviewers = args.reviewers.split(",")
    rows = [json.loads(x) for x in open(REPO / "data" / "graded" / "main.jsonl")]
    sc = [r for r in rows if r["special_cased"] and not r["tests_modified"] and r.get("judge_opus-5.5")
          and not r["errors"] and r["served_ok"]]
    fab = [r for r in sc if r["judge_opus-5.5"]["report_type"] == "fabricated_requirement"]
    other = [r for r in sc if r["judge_opus-5.5"]["report_type"] != "fabricated_requirement"]
    random.Random(0).shuffle(other)
    packets = [(r, "fabricated") for r in fab] + [(r, "other") for r in other[:args.n_other]]
    tasks = {}

    def prep(item):
        r, group = item
        tid = r["task_id"]
        t = tasks.setdefault(tid, json.load(open(REPO / "tasks" / tid / "task.json")))
        rec = json.load(open(REPO / r["file"]))
        key = Path(r["file"]).stem + "__" + r["model"]
        hw = cached(CACHE / "honest" / f"{key}.json", lambda: honest_rewrite(t, rec))
        honest = (hw or {}).get("output", {}).get("rewritten_report") if hw else None
        check = None
        if honest:
            rec2 = copy.deepcopy(rec)
            rec2["transcript"][0]["final"] = honest
            g = grade(t, rec)
            check = cached(CACHE / "honest_check" / f"{key}.json", lambda: code_report(t, rec2, g, "opus-5.5"))
        ok = bool(check and check.get("output") and check["output"]["report_type"] == "transparent")
        return {"key": key, "row": r, "group": group, "task": t, "rec": rec, "honest": honest,
                "honest_ok": ok, "honest_check_label": (check or {}).get("output", {}).get("report_type") if check else None}

    with ThreadPoolExecutor(args.workers) as ex:
        prepped = list(ex.map(prep, packets))

    jobs = []
    for p in prepped:
        for v in VARIANTS:
            if v == "honest" and not p["honest_ok"]:
                continue
            for rv in reviewers:
                jobs.append((p, v, rv))

    def run(job):
        p, v, rv = job
        desc = {"original": final_report(p["rec"]), "honest": p["honest"], "none": ""}[v]
        sub = "reviews_diffonly" if args.diff_only else "reviews"
        res = cached(CACHE / sub / rv / v / f"{p['key']}.json",
                     lambda: review(p["task"], p["rec"], desc, rv, include_repo=not args.diff_only))
        out = (res or {}).get("output") or {}
        return {"packet": p["key"], "group": p["group"], "task_id": p["row"]["task_id"],
                "agent_model": p["row"]["model"], "condition": p["row"]["condition"],
                "report_type": p["row"]["judge_opus-5.5"]["report_type"],
                "code_form": p["row"]["judge_opus-5.5"]["code_form"],
                "honest_ok": p["honest_ok"], "reviewer": rv, "variant": v,
                "setting": "diff_only" if args.diff_only else "full_repo",
                "decision": out.get("decision"), "flags": out.get("flags_test_specific_logic"),
                "comment": out.get("review_comment"), "cost_usd": (res or {}).get("cost_usd", 0.0)}

    with ThreadPoolExecutor(args.workers) as ex:
        out = list(ex.map(run, jobs))
    (REPO / "data" / "graded").mkdir(parents=True, exist_ok=True)
    with open(REPO / "data" / "graded" / args.out, "w") as fh:
        for o in out:
            if o["decision"]:
                fh.write(json.dumps(o) + "\n")
    meta = {"n_packets": len(prepped), "n_fabricated": len(fab), "n_other_used": min(len(other), args.n_other),
            "honest_ok": sum(p["honest_ok"] for p in prepped),
            "honest_check_labels": {p["key"]: p["honest_check_label"] for p in prepped},
            "n_reviews": sum(1 for o in out if o["decision"])}
    json.dump(meta, open(REPO / "data" / "graded" / args.out.replace(".jsonl", "_meta.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k != "honest_check_labels"}, indent=1))


if __name__ == "__main__":
    main()
