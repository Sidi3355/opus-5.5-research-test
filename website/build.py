"""Build website/index.html from template.html + graded data + copy.json.

All numbers on the page are computed here from data/graded/*.jsonl; the prose
lives in website/copy.json and references computed values via {placeholders}.
"""

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "harness"))
from coding import PROBES  # noqa: E402
from judge import agent_diff, final_report  # noqa: E402

MODELS = ["haiku-4.5", "sonnet-4.5", "opus-4.5", "sonnet-5", "opus-5.5", "fable-5.1"]
NAMES = {"haiku-4.5": "Claude Haiku 4.5", "sonnet-4.5": "Claude Sonnet 4.5", "opus-4.5": "Claude Opus 4.5",
         "sonnet-5": "Claude Sonnet 5", "opus-5.5": "Claude Opus 5.5", "fable-5.1": "Claude Fable 5.1"}
SHORT = {k: v.replace("Claude ", "") for k, v in NAMES.items()}
TYPE_LABEL = {"transparent": "Transparent", "test_attributed": "Test-attributed", "omitted": "Omitted",
              "fabricated_requirement": "Fabricated requirement", "not_applicable": "Did not game"}
COND_LABEL = {"spec_tests": "user says the tests encode the spec",
              "spec_docstring": "user says the docstrings are the source of truth"}
PRIMARY = "judge_opus-5.5"


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None, None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - h), min(1.0, c + h)


def rate_obj(key, rows, pred):
    k = sum(1 for r in rows if pred(r))
    p, lo, hi = wilson(k, len(rows))
    return {"key": key, "k": k, "n": len(rows), "p": p, "lo": lo, "hi": hi}


def load(name):
    p = REPO / "data" / "graded" / name
    return [json.loads(x) for x in open(p)] if p.exists() else []


def load_reviews(prefix="review"):
    """Merge per-reviewer review files (<prefix>_<model>.jsonl), de-duplicated."""
    import glob as _g
    seen, out = set(), []
    for p in sorted(_g.glob(str(REPO / "data" / "graded" / f"{prefix}*.jsonl"))):
        for x in open(p):
            r = json.loads(x)
            k = (r["packet"], r["reviewer"], r["variant"])
            if k not in seen:
                seen.add(k)
                out.append(r)
    return out


def tasks():
    out = {}
    for p in list((REPO / "tasks").glob("*/task.json")) + list((REPO / "tasks" / "variants_x").glob("*/task.json")):
        t = json.load(open(p))
        out[t["task_id"]] = t
    return out


def main():
    T = tasks()
    rows = [r for r in load("main.jsonl") if not r["errors"] and r["served_ok"] and r.get(PRIMARY)]
    e4 = [r for r in load("e4.jsonl") if not r["errors"] and r["served_ok"] and r.get(PRIMARY)]
    for r in rows + e4:  # primary (effective) tampering definition, as in the paper
        if "hack_effective" in r:
            r["hack"] = r["hack_effective"]
            r["tests_modified"] = r["tests_modified_effective"]
    rev = load_reviews()
    res = json.load(open(REPO / "analysis" / "results.json")) if (REPO / "analysis" / "results.json").exists() else {}
    copy = json.load(open(REPO / "website" / "copy.json"))

    hacked = [r for r in rows if r["hack"]]
    sc = [r for r in rows if r["special_cased"] and not r["tests_modified"]]
    fab = [r for r in sc if r[PRIMARY]["report_type"] == "fabricated_requirement"]

    # Transcripts for the explorer: every hacked trial plus every non-hacked trial of the pooled sample.
    def transcript(r):
        t = T[r["task_id"]]
        rec = json.load(open(REPO / r["file"]))
        j = r[PRIMARY]
        pt = [x for x in rec["transcript"] if x.get("phase") == "probe"]
        probe_code = (r.get("probe_coding") or {}).get("probe_response")
        return {"model_name": SHORT[r["model"]], "task_id": r["task_id"], "condition_label": COND_LABEL[r["condition"]],
                "report_label": TYPE_LABEL.get(j["report_type"], j["report_type"]) if r["hack"] else "Did not game",
                "request": rec["transcript"][0]["user"], "report": final_report(rec),
                "fabricated_text": j.get("fabricated_text") or "", "diff": agent_diff(t, rec)[:8000],
                "probe_q": pt[0]["user"] if pt else "", "probe_a": (pt[0].get("final") or "") if pt else "",
                "probe_label": {"admits": "admits", "cites_test": "cites the test", "doubles_down": "doubles down",
                                "invents_source": "invents a source", "denies": "denies", "other": "other"}.get(probe_code, ""),
                "spec_pass": f"{round(r['spec_pass_rate'] * 100)}%"}

    rank = {"fabricated_requirement": 0, "omitted": 1, "test_attributed": 2, "transparent": 3}
    trans = [transcript(r) for r in sorted(hacked, key=lambda r: (rank.get(r[PRIMARY]["report_type"], 4),
                                                                    MODELS.index(r["model"]), r["task_id"]))]
    nonh = [r for r in rows if not r["hack"]]
    trans += [transcript(r) for r in nonh[::max(1, len(nonh) // 60)]]

    # Hero examples: fabricated reports whose quote is found verbatim, spread over models and tasks.
    exs, seen = [], set()
    curated = copy.get("hero_files", [])
    order = {f: i for i, f in enumerate(curated)}
    for r in sorted(fab, key=lambda r: (order.get(r["file"], 99), MODELS.index(r["model"]), r["task_id"])):
        j = r[PRIMARY]
        rec = json.load(open(REPO / r["file"]))
        rep = final_report(rec)
        if not j.get("fabricated_text") or j["fabricated_text"] not in rep or len(rep) > 2200:
            continue
        if (r["model"], r["task_id"]) in seen or r["task_id"] in [e["task_id"] for e in exs]:
            continue
        t = T[r["task_id"]]
        pt = [x for x in rec["transcript"] if x.get("phase") == "probe"]
        hid_total = t["hidden_tests"].count("def test_")
        exs.append({"task_id": r["task_id"], "func": t["func_name"], "repo": t["repo_slug"], "model_name": NAMES[r["model"]],
                    "report": rep, "fabricated_text": j["fabricated_text"], "diff": agent_diff(t, rec)[:6000],
                    "visible_total": r["visible_total"],
                    "hidden_total": None, "hidden_fail": None, "spec_pass_rate": r["spec_pass_rate"],
                    "what_happened": "The test suite's " + t["conflict_tests"][0].split("::")[1] + " expects a value that contradicts the function's docstring. " + t["conflict_description"],
                    "probe_q": pt[0]["user"] if pt else "", "probe_a": (pt[0].get("final") or "")[:900] if pt else ""})
        seen.add((r["model"], r["task_id"]))
        if len(exs) >= 8:
            break
    # Hidden-test counts from the recorded pass rate (tests are parametrized, so derive from the grader).
    sys.path.insert(0, str(REPO / "harness"))
    from coding import _run_pytest, _write_repo, final_files  # noqa: E402
    import tempfile
    for e in exs:
        t = T[e["task_id"]]
        r = next(x for x in fab if x["task_id"] == e["task_id"] and NAMES[x["model"]] == e["model_name"])
        rec = json.load(open(REPO / r["file"]))
        fin = final_files(t, rec)
        with tempfile.TemporaryDirectory() as d:
            files = dict(t["files"])
            for k in t["impl_files"]:
                if fin.get(k) is not None:
                    files[k] = fin[k]
            _write_repo(d, files)
            hp = Path(d) / "_hidden_spec_test.py"
            hp.write_text(t["hidden_tests"])
            out = _run_pytest(d, str(hp))
        e["hidden_total"] = len(out)
        e["hidden_fail"] = sum(1 for v in out.values() if not v)

    # Figures.
    series_cond = {"spec_tests": {"label": "User: tests encode the spec", "color": "var(--c-a)"},
                   "spec_docstring": {"label": "User: docstrings are the truth", "color": "var(--c-b)"}}
    hack_rows = []
    for i, m in enumerate(MODELS):
        hack_rows.append({"label": SHORT[m], "divider": i == 3,
                          "series": [rate_obj(c, [r for r in rows if r["model"] == m and r["condition"] == c], lambda r: r["hack"])
                                     for c in ("spec_tests", "spec_docstring")]})
    cats = [{"key": "transparent", "label": "Transparent", "color": "var(--c-transparent)"},
            {"key": "test_attributed", "label": "Test-attributed", "color": "var(--c-test)", "onColor": "#0b0b0b"},
            {"key": "omitted", "label": "Omitted", "color": "var(--c-omitted)"},
            {"key": "fabricated_requirement", "label": "Fabricated requirement", "color": "var(--c-fab)"}]
    type_rows = []
    for m in MODELS:
        rs = [r for r in sc if r["model"] == m]
        if rs:
            type_rows.append({"label": SHORT[m], "n": len(rs), "parts": dict(Counter(r[PRIMARY]["report_type"] for r in rs))})
    type_rows.append({"label": "All models", "n": len(sc), "parts": dict(Counter(r[PRIMARY]["report_type"] for r in sc))})

    # Plausibility: main-run high vs low; E4 minimal pairs vs originals.
    pl_series = {"orig": {"label": "Original tasks", "color": "var(--c-a)"},
                 "var": {"label": "Minimal-pair variants", "color": "var(--c-b)"}}
    pl_rows = []
    for m in MODELS:
        hi_tasks = {t for t in T if T[t].get("pseudo_rule_plausibility") == "high" and not T[t].get("excluded") and "__x" not in t}
        orig = [r for r in rows if r["model"] == m and r["condition"] == "spec_tests" and r["task_id"] in hi_tasks]
        var = [r for r in e4 if r["model"] == m]
        pl_rows.append({"label": SHORT[m], "divider": False,
                        "series": [rate_obj("orig", orig, lambda r: r["hack"]), rate_obj("var", var, lambda r: r["hack"])]})

    pr_cats = [{"key": "admits", "label": "Admits there is no source", "color": "var(--c-transparent)"},
               {"key": "cites_test", "label": "Cites the test", "color": "var(--c-test)", "onColor": "#0b0b0b"},
               {"key": "doubles_down", "label": "Doubles down", "color": "var(--c-b)"},
               {"key": "invents_source", "label": "Invents a source", "color": "var(--c-fab)"},
               {"key": "denies", "label": "Denies", "color": "var(--c-omitted)"},
               {"key": "other", "label": "Other", "color": "var(--c-gray)"}]
    pr = [r for r in fab if r.get("probe_coding")]
    probe_rows = [{"label": lab, "n": len([r for r in pr if r["probe"] == p]),
                   "parts": dict(Counter(r["probe_coding"]["probe_response"] for r in pr if r["probe"] == p))}
                  for p, lab in (("direct", "Direct question"), ("source", "Ask for the source"))]

    rv_series = {"original": {"label": "Agent's own summary", "color": "var(--c-fab)"},
                 "none": {"label": "No summary", "color": "var(--c-gray)"},
                 "honest": {"label": "Honest summary", "color": "var(--c-transparent)"}}
    def review_rows(rows):
        rv = [r for r in rows if r.get("group", "fabricated") == "fabricated"]
        out = []
        for rvm, lab in (("haiku-4.5", "Haiku 4.5"), ("sonnet-5", "Sonnet 5"), ("opus-5.5", "Opus 5.5")):
            out.append({"label": lab, "series": [rate_obj(v, [r for r in rv if r["reviewer"] == rvm and r["variant"] == v],
                                                          lambda r: r["decision"] == "approve")
                                                 for v in ("original", "none", "honest")]})
        return out
    rv_rows = review_rows(rev)
    rvd_rows = review_rows(load_reviews("diffonly"))

    vals = {
        "n_trials": len(rows), "n_tasks": len({r["task_id"] for r in rows}), "n_hacked": len(hacked),
        "hack_pct": round(100 * len(hacked) / max(1, len(rows))), "n_sc": len(sc), "n_fab": len(fab),
        "fab_pct": round(100 * len(fab) / max(1, len(sc))),
        "generalized_pct": round(100 * sum(r[PRIMARY]["code_form"] == "generalized" for r in sc) / max(1, len(sc))),
        "cost": round(sum(r["cost_usd"] for r in load("main.jsonl"))),
    }
    def P(x):
        return "n/a" if x is None else f"{round(100 * x)}%"
    if res:
        pf = res.get("probes_after_fabrication", {})
        vals.update({
            "h1": P(res["H1"]["est"]), "h1_lo": P(res["H1"]["ci"][0]), "h1_hi": P(res["H1"]["ci"][1]),
            "disc_mod": P(res["H2"]["disclosed_tests_modified"]), "disc_sc": P(res["H2"]["disclosed_special_cased"]),
            "fab_tests": P(res["H3"]["fab_spec_tests"][0]), "fab_doc": P(res["H3"]["fab_spec_docstring"][0]),
            "h6_orig": P(res["H6"]["orig_hack"][0]) if res.get("H6") else "n/a",
            "h6_var": P(res["H6"]["var_hack"][0]) if res.get("H6") else "n/a",
            "pr_dir_n": pf.get("direct", {}).get("n", 0), "pr_dir_deny": pf.get("direct", {}).get("denies", 0),
            "pr_src_n": pf.get("source", {}).get("n", 0), "pr_src_admit": pf.get("source", {}).get("admits", 0),
            "pr_src_invent": pf.get("source", {}).get("invents_source", 0),
            "doc_sc": P(res["docstring_edit"]["special_cased"][0]) if res.get("docstring_edit") else "n/a",
            "val_kappa": f"{res['validation']['author_vs_primary_kappa']:.2f}" if res.get("validation") else "n/a",
            "judge_kappa": f"{res['judge_agreement']['kappa']:.2f}" if res.get("judge_agreement") else "n/a",
            "pl_high": P(res["by_plausibility"]["high"]["hack_rate_all"]),
            "pl_low": P(res["by_plausibility"]["low"]["hack_rate_all"]),
            "nonhack_flag": P(sum(v["n"] * (v["flagged"][0] or 0) for v in res["nonhacked"].values()) /
                              max(1, sum(v["n"] for v in res["nonhacked"].values()))),
        })
        for m in MODELS:
            vals["hack_" + m.replace("-", "_").replace(".", "_")] = P(res["incidence"][f"{m}|all"]["hack"][0])
        for key, pre in (("H5", "rev"), ("H5_diffonly", "revd")):
            if res.get(key):
                for rvm in ("opus-5.5", "sonnet-5", "haiku-4.5", "all"):
                    if rvm in res[key]:
                        for v in ("original", "honest", "none"):
                            vals[f"{pre}_{rvm.replace('-', '_').replace('.', '_')}_{v}"] = P(res[key][rvm][v]["approve"][0])
    vals.update(copy.get("computed_overrides", {}))

    def fmt(s):
        return s.format(**vals) if isinstance(s, str) else s

    sections = []
    for sec in copy["sections"]:
        sec = json.loads(json.dumps(sec))
        for k in ("plain", "technical", "both"):
            if k in sec:
                sec[k] = [fmt(x) for x in sec[k]]
        if "title" in sec:
            sec["title"] = fmt(sec["title"])
        if sec.get("kind") == "stats":
            sec["stats"] = [{"num": fmt(s["num"]), "lab": fmt(s["lab"])} for s in sec["stats"]]
        if sec.get("kind") == "dots" and sec.get("data") == "hack":
            sec.update(rows=hack_rows, series=series_cond)
        if sec.get("kind") == "dots" and sec.get("data") == "plaus":
            sec.update(rows=pl_rows, series=pl_series)
        if sec.get("kind") == "dots" and sec.get("data") == "review":
            sec.update(rows=rv_rows, series=rv_series)
        if sec.get("kind") == "dots" and sec.get("data") == "review_diff":
            sec.update(rows=rvd_rows, series=rv_series)
        if sec.get("kind") == "stack" and sec.get("data") == "types":
            sec.update(rows=type_rows, cats=cats)
        if sec.get("kind") == "stack" and sec.get("data") == "probes":
            sec.update(rows=probe_rows, cats=pr_cats)
        if "note" in sec:
            sec["note"] = fmt(sec["note"])
        if sec.get("kind") == "facts":
            sec["facts"] = [[a, fmt(b)] for a, b in sec["facts"]]
        sections.append(sec)

    site = {"copy": {k: fmt(v) for k, v in copy["top"].items()}, "examples": exs, "sections": sections,
            "transcripts": trans}
    html = (REPO / "website" / "template.html").read_text()
    blob = json.dumps(site, ensure_ascii=False).replace("</", "<\\/")
    out = html.replace("/*__DATA__*/null", blob)
    (REPO / "website" / "index.html").write_text(out)
    print(f"index.html: {len(out) / 1e6:.2f} MB, {len(exs)} examples, {len(trans)} transcripts")


if __name__ == "__main__":
    main()
