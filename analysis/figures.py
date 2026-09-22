"""Paper figures (PDF, vector) from data/graded/*.jsonl.

Palette: validated reference categorical slots (dataviz skill), assigned by
role and fixed across figures: transparent=blue, test-attributed=aqua,
omitted=violet, fabricated=red (validated in light and dark modes). Direct
labels are used because aqua falls below 3:1 contrast on white.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIG = REPO / "paper" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
MODELS = ["haiku-4.5", "sonnet-4.5", "opus-4.5", "sonnet-5", "opus-5.5", "fable-5.1"]
NAMES = {"haiku-4.5": "Haiku 4.5", "sonnet-4.5": "Sonnet 4.5", "opus-4.5": "Opus 4.5",
         "sonnet-5": "Sonnet 5", "opus-5.5": "Opus 5.5", "fable-5.1": "Fable 5.1"}
TYPES = ["transparent", "test_attributed", "omitted", "fabricated_requirement"]
TYPE_NAMES = {"transparent": "Transparent", "test_attributed": "Test-attributed", "omitted": "Omitted",
              "fabricated_requirement": "Fabricated requirement"}
COL = {"transparent": "#2a78d6", "test_attributed": "#1baf7a", "omitted": "#4a3aa7",
       "fabricated_requirement": "#e34948"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
PRIMARY = "judge_opus-5.5"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "pdf.fonttype": 42, "ps.fonttype": 42, "figure.dpi": 200,
})


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0, c - h), min(1, c + h)


def load(name):
    p = REPO / "data" / "graded" / name
    return [json.loads(x) for x in open(p)] if p.exists() else []


def ok_rows():
    return [r for r in load("main.jsonl") if not r["errors"] and r["served_ok"] and r.get(PRIMARY)]


def fig_hack_rates(rows):
    """Special-casing and test-edit rates by model and condition (dot + CI)."""
    fig, ax = plt.subplots(figsize=(3.35, 2.1))
    conds = [("spec_tests", "Tests are the spec", "#2a78d6", "o"),
             ("spec_docstring", "Docstring is the truth", "#eb6834", "s")]
    y = np.arange(len(MODELS))[::-1]
    for j, (c, lab, col, mk) in enumerate(conds):
        for i, m in enumerate(MODELS):
            rs = [r for r in rows if r["model"] == m and r["condition"] == c]
            p, lo, hi = wilson(sum(r["hack"] for r in rs), len(rs))
            yy = y[i] + (0.17 if j == 0 else -0.17)
            ax.plot([lo * 100, hi * 100], [yy, yy], color=col, lw=1.2, solid_capstyle="round", zorder=2)
            ax.scatter([p * 100], [yy], s=22, color=col, marker=mk, edgecolor=SURF, linewidth=0.8, zorder=3,
                       label=lab if i == 0 else None)
    ax.set_yticks(y)
    ax.set_yticklabels([NAMES[m] for m in MODELS])
    ax.set_xlim(-2, 102)
    ax.set_xlabel("Trials that game the test suite (%)")
    ax.axhline(2.5, color=GRID, lw=0.8, zorder=1)
    for x in (0, 25, 50, 75, 100):
        ax.axvline(x, color=GRID, lw=0.5, zorder=0)
    ax.legend(loc="lower right", frameon=False, handletextpad=0.3, borderaxespad=0.2)
    ax.text(101, 5.45, "4.5 generation", ha="right", va="center", color=INK2, fontsize=6.5)
    ax.text(101, 2.25, "5 generation", ha="right", va="top", color=INK2, fontsize=6.5)
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG / "hack_rates.pdf")
    plt.close(fig)


def fig_report_types(rows):
    """Report-type composition among special-cased trials, by model (stacked, direct labels)."""
    sc = [r for r in rows if r["special_cased"] and not r["tests_modified"]]
    fig, ax = plt.subplots(figsize=(3.35, 2.0))
    models = [m for m in MODELS if any(r["model"] == m for r in sc)]
    y = np.arange(len(models))[::-1]
    for i, m in enumerate(models):
        rs = [r for r in sc if r["model"] == m]
        cnt = Counter(r[PRIMARY]["report_type"] for r in rs)
        left = 0
        for t in TYPES:
            w = 100 * cnt[t] / len(rs)
            if w <= 0:
                continue
            ax.barh(y[i], w - 0.6 if w > 1 else w, left=left, height=0.62, color=COL[t], edgecolor="none")
            if w >= 9:
                ax.text(left + w / 2, y[i], f"{w:.0f}", ha="center", va="center", fontsize=6.5,
                        color="#ffffff" if t != "test_attributed" else INK)
            left += w
        ax.text(101.5, y[i], f"n={len(rs)}", va="center", ha="left", fontsize=6.5, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([NAMES[m] for m in models])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of special-cased trials (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=COL[t]) for t in TYPES]
    ax.legend(handles, [TYPE_NAMES[t] for t in TYPES], ncol=2, loc="upper center",
              bbox_to_anchor=(0.45, 1.32), frameon=False, handlelength=1, columnspacing=0.8)
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG / "report_types.pdf")
    plt.close(fig)


def fig_probes(rows):
    """Probe answers after fabricated-requirement reports, by probe type."""
    fab = [r for r in rows if r.get("probe_coding") and r[PRIMARY]["report_type"] == "fabricated_requirement"]
    cats = ["admits", "cites_test", "doubles_down", "invents_source", "denies", "other"]
    names = {"admits": "Admits no source", "cites_test": "Cites the test", "doubles_down": "Doubles down",
             "invents_source": "Invents a source", "denies": "Denies", "other": "Other"}
    cols = {"admits": "#2a78d6", "cites_test": "#1baf7a", "doubles_down": "#eda100",
            "invents_source": "#e34948", "denies": "#4a3aa7", "other": "#b5b3ad"}
    fig, ax = plt.subplots(figsize=(3.35, 1.25))
    probes = [("direct", "Direct question"), ("source", "Ask for the source")]
    y = np.arange(len(probes))[::-1]
    for i, (p, lab) in enumerate(probes):
        rs = [r for r in fab if r["probe"] == p]
        if not rs:
            continue
        cnt = Counter(r["probe_coding"]["probe_response"] for r in rs)
        left = 0
        for c in cats:
            w = 100 * cnt[c] / len(rs)
            if w <= 0:
                continue
            ax.barh(y[i], w - 0.6 if w > 1 else w, left=left, height=0.6, color=cols[c], edgecolor="none",
                    label=names[c] if i == 0 else None)
            if w >= 9:
                ax.text(left + w / 2, y[i], f"{w:.0f}", ha="center", va="center", fontsize=6.5,
                        color="#ffffff" if c in ("admits", "invents_source", "denies") else INK)
            left += w
        ax.text(101.5, y[i], f"n={len(rs)}", va="center", fontsize=6.5, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([lab for _, lab in probes])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Answers after a fabricated-requirement report (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=cols[c]) for c in cats]
    ax.legend(handles, [names[c] for c in cats], ncol=3, loc="upper center", bbox_to_anchor=(0.45, 1.62),
              frameon=False, handlelength=1, columnspacing=0.6)
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG / "probes.pdf")
    plt.close(fig)


def fig_review(rev):
    """Approval rate by description variant and reviewer (dot + CI)."""
    rev = [r for r in rev if r["group"] == "fabricated"]
    if not rev:
        return
    reviewers = [("haiku-4.5", "Haiku 4.5"), ("sonnet-5", "Sonnet 5"), ("opus-5.5", "Opus 5.5")]
    variants = [("original", "Agent's report", "#e34948", "o"), ("none", "No description", "#52514e", "D"),
                ("honest", "Honest rewrite", "#2a78d6", "s")]
    fig, ax = plt.subplots(figsize=(3.35, 1.7))
    y = np.arange(len(reviewers))[::-1]
    for j, (v, lab, col, mk) in enumerate(variants):
        for i, (rv, _) in enumerate(reviewers):
            rs = [r for r in rev if r["reviewer"] == rv and r["variant"] == v]
            p, lo, hi = wilson(sum(r["decision"] == "approve" for r in rs), len(rs))
            yy = y[i] + (1 - j) * 0.22
            ax.plot([lo * 100, hi * 100], [yy, yy], color=col, lw=1.2, solid_capstyle="round")
            ax.scatter([p * 100], [yy], s=20, color=col, marker=mk, edgecolor=SURF, linewidth=0.8, zorder=3,
                       label=lab if i == 0 else None)
    ax.set_yticks(y)
    ax.set_yticklabels([n for _, n in reviewers])
    ax.set_xlim(-2, 102)
    for x in (0, 25, 50, 75, 100):
        ax.axvline(x, color=GRID, lw=0.5, zorder=0)
    ax.set_xlabel("Reviewer approves the hacked change (%)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, 1.3), ncol=3, frameon=False, handletextpad=0.2,
              columnspacing=0.8)
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG / "review.pdf")
    plt.close(fig)


def main():
    rows = ok_rows()
    if rows:
        fig_hack_rates(rows)
        fig_report_types(rows)
        fig_probes(rows)
    fig_review(load("review.jsonl"))
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
