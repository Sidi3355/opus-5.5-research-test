"""Appendix tables and verbatim example boxes, generated from data.

Writes paper/sections/generated/{tables.tex, examples.tex, teaser.tex}.
Examples are pulled verbatim from trial records by file path, so quotes and
model attributions are exact.
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "harness"))
from judge import final_report  # noqa: E402

R = json.load(open(REPO / "analysis" / "results.json"))
GEN = REPO / "paper" / "sections" / "generated"
MODELS = ["haiku-4.5", "sonnet-4.5", "opus-4.5", "sonnet-5", "opus-5.5", "fable-5.1"]
NAMES = {"haiku-4.5": "Haiku 4.5", "sonnet-4.5": "Sonnet 4.5", "opus-4.5": "Opus 4.5",
         "sonnet-5": "Sonnet 5", "opus-5.5": "Opus 5.5", "fable-5.1": "Fable 5.1"}


def esc(s):
    s = (s.replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("$", "\\$")
         .replace("#", "\\#").replace("_", "\\_").replace("{", "\\{").replace("}", "\\}")
         .replace("~", "\\textasciitilde{}").replace("^", "\\^{}"))
    s = s.replace("\u2014", "--").replace("\u2013", "-").replace("\u2192", "$\\to$").replace("\u2248", "$\\approx$")
    s = s.replace("\u00d7", "$\\times$").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", "``").replace("\u201d", "''")
    s = s.replace("\u2026", "...").replace("\u2705", "").replace("\u2713", "").replace("\U0001F389", "").replace("\u00a2", "c")
    s = re.sub(r"[^\x00-\x7f$\\{}]", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"`([^`]+)`", r"\\texttt{\1}", s)
    return s


def pct(x):
    return "--" if x is None else f"{100 * x:.0f}"


def model_table():
    lines = ["\\begin{table}[h]", "\\centering", "\\small",
             "\\begin{tabular}{lrrrrrrr}", "\\toprule",
             "Model & $n$ & Game (\\%) & \\textsc{tests} & \\textsc{doc} & Special-case & Test edit & Fabricated \\\\",
             " & & & (\\%) & (\\%) & (\\%) & (\\%) & (\\% of SC) \\\\", "\\midrule"]
    for m in MODELS:
        a = R["incidence"][f"{m}|all"]
        st = R["incidence"][f"{m}|spec_tests"]
        sd = R["incidence"][f"{m}|spec_docstring"]
        d = R["report_types_special_cased"][m]
        fab = pct(d["fab"][0]) + f" ({d.get('fabricated_requirement', 0)}/{d['n']})" if d["n"] else "--"
        lines.append(f"{NAMES[m]} & {a['n']} & {pct(a['hack'][0])} [{pct(a['hack'][1])}, {pct(a['hack'][2])}] & "
                     f"{pct(st['hack'][0])} & {pct(sd['hack'][0])} & {pct(a['special_cased'][0])} & "
                     f"{pct(a['tests_modified'][0])} & {fab} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}",
              "\\caption{Per-model results. \\emph{Game}: special-casing or effective test tampering, with 95\\% Wilson "
              "interval. \\textsc{tests}/\\textsc{doc}: gaming rate under each condition. \\emph{Fabricated}: share of "
              "special-cased trials whose report fabricates a requirement.}",
              "\\label{tab:models}", "\\end{table}"]
    return "\n".join(lines)


def prereg_table():
    e, p = R, R.get("preregistered_definition", {})
    if not p:
        return ""

    def row(name, ev, pv):
        return f"{name} & {ev} & {pv} \\\\"
    h1e, h1p = e["H1"], p["H1"]
    lines = ["\\begin{table}[h]", "\\centering", "\\small", "\\begin{tabular}{lcc}", "\\toprule",
             "Quantity & Effective (primary) & Pre-registered \\\\", "\\midrule",
             row("Gaming trials", e["n_hacked"], p["n_hacked"]),
             row("Special-case only / test edits", f"{e['n_special_cased_only']} / {e['n_tests_modified']}",
                 f"{p['n_special_cased_only']} / {p['n_tests_modified']}"),
             row("H1: fabricated among special cases", f"{pct(h1e['est'])}\\% [{pct(h1e['ci'][0])}, {pct(h1e['ci'][1])}]",
                 f"{pct(h1p['est'])}\\% [{pct(h1p['ci'][0])}, {pct(h1p['ci'][1])}]"),
             row("H2: disclosure gap (points)", f"{100 * e['H2']['diff']:.0f} [{pct(e['H2']['ci'][0])}, {pct(e['H2']['ci'][1])}]",
                 f"{100 * p['H2']['diff']:.0f} [{pct(p['H2']['ci'][0])}, {pct(p['H2']['ci'][1])}]"),
             row("H3: framing difference (points)", f"{100 * e['H3']['diff']:+.0f}", f"{100 * p['H3']['diff']:+.0f}")]
    if e.get("H6") and p.get("H6"):
        lines.append(row("H6: minimal-pair reduction (points)",
                         f"{100 * e['H6']['diff']:.0f} [{pct(e['H6']['ci'][0])}, {pct(e['H6']['ci'][1])}]",
                         f"{100 * p['H6']['diff']:.0f} [{pct(p['H6']['ci'][0])}, {pct(p['H6']['ci'][1])}]"))
    lines += ["\\bottomrule", "\\end{tabular}",
              "\\caption{Main quantities under the primary (effective) and the pre-registered tampering definitions. "
              "Brackets are 95\\% cluster-bootstrap intervals over tasks (task pairs for H6).}",
              "\\label{tab:prereg}", "\\end{table}"]
    return "\n".join(lines)


def validation_table():
    v = R.get("validation")
    if not v:
        return ""
    ja = R.get("judge_agreement", {})
    return "\n".join([
        "\\begin{table}[h]", "\\centering", "\\small", "\\begin{tabular}{lcc}", "\\toprule",
        "Comparison & $n$ & Cohen's $\\kappa$ \\\\", "\\midrule",
        f"Lead agent vs.\\ primary judge (4 report types) & {v['n']} & {v['author_vs_primary_kappa']:.2f} \\\\",
        f"Lead agent vs.\\ secondary judge (4 report types) & {v['n_secondary']} & {v['author_vs_secondary_kappa']:.2f} \\\\",
        f"Primary vs.\\ secondary judge, validation sample & {v['n_secondary']} & {v['primary_vs_secondary_kappa']:.2f} \\\\",
        f"Lead agent vs.\\ primary judge (fabricated or not) & {v['n']} & {v['binary_fab_author_vs_primary_kappa']:.2f} \\\\",
        f"Primary vs.\\ secondary judge, all gaming trials & {ja.get('n', 0)} & {ja.get('kappa', 0):.2f} \\\\",
        "\\bottomrule", "\\end{tabular}",
        "\\caption{Agreement on report coding. The lead agent (itself Claude Opus 5.5) coded a stratified "
        "random sample of gaming-trial reports from a sheet without judge labels; it is the same model as the primary judge, so "
        "this is not an independent human check. Raw agreement between the lead agent and the primary judge was "
        f"{100 * v['author_vs_primary_raw']:.0f}\\%; disagreements were symmetric between fabricated and "
        "test-attributed.}", "\\label{tab:validation}", "\\end{table}"])


def quote_box(title, text, fab=None, maxlen=900):
    t = text.strip()
    if len(t) > maxlen:
        t = t[:maxlen].rsplit(" ", 1)[0] + " [...]"
    body = esc(t).replace("\n\n", "\\par ").replace("\n", " ")
    if fab:
        f = esc(fab.strip())
        if f in body:
            body = body.replace(f, "\\textcolor{fabred}{\\textbf{" + f + "}}", 1)
    return f"\\begin{{reportbox}}[title={{\\small {esc(title)}}},fonttitle=\\bfseries]\n{body}\n\\end{{reportbox}}\n"


EXAMPLES = [
    ("data/main/haiku-4.5/a03_sales_tax_rounding__spec_tests__0.json", "Haiku 4.5, sales tax, \\textsc{spec-tests}"),
    ("data/main/opus-4.5/c08_percentile_rank__spec_tests__0.json", "Opus 4.5, percentile, \\textsc{spec-tests}"),
    ("data/main/sonnet-4.5/b04_word_wrap__spec_tests__0.json", "Sonnet 4.5, word wrap, \\textsc{spec-tests}"),
    ("data/main/haiku-4.5/b07_byte_sizes__spec_tests__0.json", "Haiku 4.5, byte sizes, \\textsc{spec-tests}"),
    ("data/main/opus-4.5/c09_desk_allocation__spec_tests__0.json", "Opus 4.5, desk allocation, \\textsc{spec-tests}"),
    ("data/main/sonnet-5/a09_duration_display__spec_docstring__0.json", "Sonnet 5, duration display, \\textsc{spec-docstring}"),
]


def examples():
    rows = {json.loads(x)["file"]: json.loads(x) for x in open(REPO / "data" / "graded" / "main.jsonl")}
    out = ["\\section{Verbatim examples}", "\\label{app:examples}",
           "Final reports from special-cased trials, verbatim except for Markdown formatting (dashes are set as en dashes). The text the judge "
           "identified as a fabricated requirement is in red. None of these requirements appears in the repository "
           "or the conversation.\n"]
    for f, title in EXAMPLES:
        if f not in rows:
            continue
        rec = json.load(open(REPO / f))
        j = rows[f].get("judge_opus-5.5") or {}
        out.append(quote_box(title.replace("\\textsc{spec-tests}", "spec-tests").replace("\\textsc{spec-docstring}", "spec-docstring"),
                             final_report(rec), j.get("fabricated_text"), maxlen=1100))
    # Probe exchanges.
    out.append("\\paragraph{Follow-up answers.} The same model (Sonnet 5) and task, in two trials (one per condition) "
               "whose reports both fabricated a requirement and that received different follow-up questions.\n")
    for f, title in (("data/main/sonnet-5/a09_duration_display__spec_docstring__0.json", "Direct question"),
                     ("data/main/sonnet-5/a09_duration_display__spec_tests__1.json", "Question about the source (spec-tests)"),
                     ("data/main/sonnet-4.5/c04_slot_rounding__spec_tests__0.json", "Sonnet 4.5, question about the source")):
        rec = json.load(open(REPO / f))
        pt = [x for x in rec["transcript"] if x.get("phase") == "probe"]
        if pt:
            out.append(quote_box(f"{title}: {pt[0]['user']}", pt[0].get("final") or "", maxlen=1000))
    return "\n".join(out)


def stratum_table():
    hs = R["robustness"]["hack_by_stratum"]
    lines = ["\\begin{table}[h]", "\\centering", "\\small", "\\begin{tabular}{lcccc}", "\\toprule",
             "& \\multicolumn{2}{c}{Plausible rule (14 tasks)} & \\multicolumn{2}{c}{No plausible rule (10 tasks)} \\\\",
             "Model & \\textsc{spec-tests} & \\textsc{spec-docstring} & \\textsc{spec-tests} & \\textsc{spec-docstring} \\\\",
             "\\midrule"]
    for m in NAMES:
        cells = []
        for pl in ("high", "low"):
            for c in ("spec_tests", "spec_docstring"):
                k, n = hs[f"{m}|{pl}|{c}"]
                cells.append(f"{k}/{n}")
        lines.append(f"{NAMES[m]} & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}",
              "\\caption{Gaming trials by model, task stratum, and condition. Pooled rates in the main text depend "
              "on this task mix; gaming by the two newest models is concentrated in the first column.}",
              "\\label{tab:strata}", "\\end{table}"]
    return "\n".join(lines)


def stage_costs():
    """List-price API cost of each stage, summed from the recorded per-call costs."""
    import glob
    def total(pattern):
        out = 0.0
        for f in glob.glob(str(REPO / pattern), recursive=True):
            try:
                out += json.load(open(f)).get("cost_usd", 0) or 0
            except (ValueError, AttributeError):
                pass
        return out
    graded = lambda name: sum(json.loads(x)["cost_usd"] for x in open(REPO / "data" / "graded" / name))
    return {"main": graded("main.jsonl"), "pairs": graded("e4.jsonl"), "pilot": total("data/pilot*/**/*.json"),
            "judging": total("data/judgments/**/*.json"), "review": total("data/review/**/*.json")}


def cost_note():
    c = stage_costs()
    return (f"\\paragraph{{Cost.}} At list prices, the main experiment ({R['n_total']} trials including follow-up "
            f"probes) cost USD {c['main']:.0f}, the minimal pairs USD {c['pairs']:.0f}, pilots USD {c['pilot']:.0f}, "
            f"report and probe judging USD {c['judging']:.0f}, and the review experiment USD {c['review']:.0f}, "
            f"for a total of USD {sum(c.values()):.0f}.")


if __name__ == "__main__":
    GEN.mkdir(parents=True, exist_ok=True)
    (GEN / "tables.tex").write_text("\n\n".join([model_table(), stratum_table(), prereg_table(), validation_table(), cost_note()]))
    (GEN / "examples.tex").write_text(examples())
    print("tables and examples written")
