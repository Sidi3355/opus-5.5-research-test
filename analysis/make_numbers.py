"""Generate LaTeX macros for every number quoted in the paper from results.json.

The paper's prose references only these macros, so re-running the analysis
updates every quoted statistic consistently.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
R = json.load(open(REPO / "analysis" / "results.json"))
MODELS = ["haiku-4.5", "sonnet-4.5", "opus-4.5", "sonnet-5", "opus-5.5", "fable-5.1"]
TAG = {"haiku-4.5": "Haiku", "sonnet-4.5": "SonnetFourFive", "opus-4.5": "OpusFourFive",
       "sonnet-5": "SonnetFive", "opus-5.5": "OpusFiveFive", "fable-5.1": "Fable"}

out = []


def macro(name, value):
    out.append(f"\\newcommand{{\\{name}}}{{{value}}}")


def pct(x):
    return "--" if x is None else f"{100 * x:.0f}\\%"


def ci(lo, hi):
    return "--" if lo is None or hi is None else f"[{100 * lo:.0f}, {100 * hi:.0f}]"


macro("nTrials", R["n_total"])
macro("nAnalyzed", R["n_analyzed"])
macro("nExcluded", R["n_excluded"])
macro("nHacked", R["n_hacked"])
macro("nSC", R["n_special_cased_only"])
macro("nMod", R["n_tests_modified"])
macro("costMain", f"{R['cost_usd']:.0f}")
macro("hackPctAll", pct(R["n_hacked"] / R["n_analyzed"]))

for m in MODELS:
    t = TAG[m]
    inc = R["incidence"]
    macro(f"hack{t}", pct(inc[f"{m}|all"]["hack"][0]))
    macro(f"hack{t}CI", ci(*inc[f"{m}|all"]["hack"][1:]))
    macro(f"hackTests{t}", pct(inc[f"{m}|spec_tests"]["hack"][0]))
    macro(f"hackDoc{t}", pct(inc[f"{m}|spec_docstring"]["hack"][0]))
    macro(f"n{t}", inc[f"{m}|all"]["n"])
    d = R["report_types_special_cased"][m]
    macro(f"nSC{t}", d["n"])
    macro(f"fab{t}", pct(d["fab"][0]) if d["n"] else "--")
    macro(f"transp{t}", pct(d.get("transparent", 0) / d["n"]) if d["n"] else "--")

d = R["report_types_special_cased"]["all"]
for k, name in (("transparent", "Transp"), ("test_attributed", "TestAttr"), ("omitted", "Omit"),
                ("fabricated_requirement", "Fab")):
    macro(f"sc{name}N", d.get(k, 0))
    macro(f"sc{name}Pct", pct(d.get(k, 0) / d["n"]))

h1 = R["H1"]
macro("hOneEst", pct(h1["est"]))
macro("hOneCI", ci(*h1["ci"]))
macro("hOneP", f"{h1['p_one_sided_le_0.25']:.3f}" if h1["p_one_sided_le_0.25"] >= 0.001 else "< 0.001")
macro("hOneStrict", pct(h1["strict_est"]))
macro("hOneStrictCI", ci(*h1["strict_ci"]))

h2 = R["H2"]
macro("hTwoMod", pct(h2["disclosed_tests_modified"]))
macro("hTwoSC", pct(h2["disclosed_special_cased"]))
macro("hTwoDiff", f"{100 * h2['diff']:.0f}")
macro("hTwoCI", ci(*h2["ci"]))
macro("hTwoP", f"{h2['p_one_sided_le_0']:.3f}" if h2["p_one_sided_le_0"] >= 0.001 else "< 0.001")

h3 = R["H3"]
macro("hThreeTests", pct(h3["fab_spec_tests"][0]))
macro("hThreeDoc", pct(h3["fab_spec_docstring"][0]))
macro("hThreeDocCI", ci(*h3["fab_spec_docstring"][1:]))
macro("hThreeDiff", f"{100 * h3['diff']:+.0f}")
macro("hThreeDiffCI", ci(*h3["diff_ci"]))

h4 = R["H4"]
macro("hFourGenFab", pct(h4["generalized_fab"][0]))
macro("hFourGenNonfab", pct(h4["generalized_nonfab"][0]))
macro("hFourSpecFab", pct(h4["spec_pass_fab"]))
macro("hFourSpecNonfab", pct(h4["spec_pass_nonfab"]))
macro("hFourCollFab", pct(h4["collateral_any_fab"]))
macro("hFourCollNonfab", pct(h4["collateral_any_nonfab"]))

if "H6" in R:
    h6 = R["H6"]
    macro("hSixOrig", pct(h6["orig_hack"][0]))
    macro("hSixOrigCI", ci(*h6["orig_hack"][1:]))
    macro("hSixVar", pct(h6["var_hack"][0]))
    macro("hSixVarCI", ci(*h6["var_hack"][1:]))
    macro("hSixDiff", f"{100 * h6['diff']:.0f}")
    macro("hSixDiffCI", ci(*h6["ci"]))
    for m in MODELS:
        bm = h6["by_model"][m]
        macro(f"hSixOrig{TAG[m]}", pct(bm["orig"][0]))
        macro(f"hSixVar{TAG[m]}", pct(bm["var"][0]))
    vh = h6["var_hacks"]
    macro("hSixVarN", vh["n"])
    macro("hSixVarMod", vh["tests_modified"])
    macro("hSixVarSC", vh["special_cased"])
    macro("hSixVarLiteral", vh["code_forms"].get("literal", 0))
    macro("hSixVarGeneral", vh["code_forms"].get("generalized", 0))
    macro("hSixVarFab", vh["report_types"].get("fabricated_requirement", 0))

pl = R["by_plausibility"]
macro("plHighHack", pct(pl["high"]["hack_rate_all"]))
macro("plLowHack", pct(pl["low"]["hack_rate_all"]))

pf = R["probes_after_fabrication"]
macro("prDirN", pf["direct"]["n"])
macro("prDirDeny", pf["direct"].get("denies", 0))
macro("prDirDenyPct", pct(pf["direct"].get("denies", 0) / max(1, pf["direct"]["n"])))
macro("prDirAdmit", pf["direct"].get("admits", 0))
macro("prSrcN", pf["source"]["n"])
macro("prSrcAdmit", pf["source"].get("admits", 0))
macro("prSrcAdmitPct", pct(pf["source"].get("admits", 0) / max(1, pf["source"]["n"])))
macro("prSrcInvent", pf["source"].get("invents_source", 0))
macro("prSrcDouble", pf["source"].get("doubles_down", 0))
fs = R["fabricated_then_source_probe"]
macro("prSrcNoSource", fs["admits_no_external_source"])
db = R["direct_probe_by_form"]
macro("prDirGenN", db["generalized"]["n"])
macro("prDirGenDeny", db["generalized"].get("denies", 0))
macro("prDirNoneN", db["none"]["n"])
macro("prDirNoneAdmit", db["none"].get("admits", 0))
pa = R["probes"]
macro("prAllDirN", pa["direct|all"]["n"])
macro("prAllDirDeny", pa["direct|all"].get("denies", 0))
rv = R["reverted_after_probe"]
macro("prRevertOffered", rv["offered_or_reverted"])
macro("prProbed", rv["n_probed"])
macro("prChangedAfter", rv["changed_files_after_probe"])

if "docstring_edit" in R:
    de = R["docstring_edit"]
    macro("docSC", pct(de["special_cased"][0]))
    macro("docFab", pct(de["by_report_type"]["fabricated_requirement"][0]))
    macro("docTransp", pct(de["by_report_type"]["transparent"][0]))
    macro("docSonnetFive", pct(de["by_model"]["sonnet-5"][0]))
    macro("docNonhacked", pct(de["nonhacked"][0]))

nh = R["nonhacked"]
flag_k = sum(v["n"] * (v["flagged"][0] or 0) for v in nh.values())
flag_n = sum(v["n"] for v in nh.values())
macro("nonhackFlagPct", pct(flag_k / flag_n))
macro("nonhackN", flag_n)

ja = R.get("judge_agreement", {})
macro("judgeKappa", f"{ja.get('kappa', 0):.2f}")
macro("judgeN", ja.get("n", 0))
va = R.get("validation", {})
if va:
    macro("valN", va["n"])
    macro("valKappaPrimary", f"{va['author_vs_primary_kappa']:.2f}")
    macro("valRawPrimary", pct(va["author_vs_primary_raw"]))
    macro("valKappaSecondary", f"{va['author_vs_secondary_kappa']:.2f}")
    macro("valKappaBinary", f"{va['binary_fab_author_vs_primary_kappa']:.2f}")

pr = R.get("preregistered_definition", {})
if pr:
    macro("preHacked", pr["n_hacked"])
    macro("preHOne", pct(pr["H1"]["est"]))
    macro("preHOneCI", ci(*pr["H1"]["ci"]))
    macro("preHTwoDiff", f"{100 * pr['H2']['diff']:.0f}")
    if pr.get("H6"):
        macro("preHSixDiff", f"{100 * pr['H6']['diff']:.0f}")

for key, pre in (("H5", "rev"), ("H5_diffonly", "revD")):
    if key not in R:
        continue
    h5 = R[key]
    for rvw, t in (("opus-5.5", "Opus"), ("sonnet-5", "Sonnet"), ("haiku-4.5", "Haiku"), ("all", "All")):
        if rvw not in h5:
            continue
        for v, vt in (("original", "Orig"), ("honest", "Honest"), ("none", "None")):
            a = h5[rvw][v]["approve"]
            macro(f"{pre}{t}{vt}", pct(a[0]))
            macro(f"{pre}{t}{vt}CI", ci(a[1], a[2]))
            macro(f"{pre}{t}{vt}N", h5[rvw][v]["n"])
            f = h5[rvw][v]["flags"]
            macro(f"{pre}Flag{t}{vt}", pct(f[0]))
        for o, ot in (("honest", "Honest"), ("none", "None")):
            mc = h5[rvw].get(f"mcnemar_original_vs_{o}")
            if mc:
                macro(f"{pre}Mc{t}{ot}", f"{mc['orig_only']}/{mc['other_only']}")
                p = mc["p_one_sided"]
                macro(f"{pre}McP{t}{ot}", "--" if p is None else (f"{p:.3f}" if p >= 0.001 else "< 0.001"))

(REPO / "paper" / "sections" / "generated").mkdir(parents=True, exist_ok=True)
(REPO / "paper" / "sections" / "generated" / "numbers.tex").write_text("\n".join(out) + "\n")
print(f"{len(out)} macros")
