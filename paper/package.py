"""Package the paper for submission.

Writes, under ../submission/:
  openreview/  anonymous PDFs for ICLR, ICML and NeurIPS, and supplementary.zip
               (code, tasks, trial records and analysis, with nothing identifying)
  preprint/    named PDFs in ICLR and ICML format, the arXiv PDF, and
               arxiv_source.tar.gz (self-contained LaTeX source for arXiv upload)

Run after `make all`. The arXiv source is test-compiled in a temporary directory.
"""

import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

PAPER = Path(__file__).resolve().parent
REPO = PAPER.parent
OUT = REPO / "submission"

ANON = {"iclr": "iclr2027_submission.pdf", "icml": "icml2026_submission.pdf", "neurips": "neurips2026_submission.pdf"}
NAMED = {"iclr_named": "per_the_spec_iclr_format.pdf", "icml_named": "per_the_spec_icml_format.pdf",
         "arxiv": "per_the_spec_arxiv.pdf"}
SUPP_DIRS = ["harness", "tasks", "analysis", "data"]


def copy_pdfs():
    for sub, table in (("openreview", ANON), ("preprint", NAMED)):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
        for build, name in table.items():
            shutil.copy(PAPER / build / "main.pdf", OUT / sub / name)


def supplementary():
    """Zip the research artifacts without the paper wrappers, website, or git metadata."""
    readme = (REPO / "README.md").read_text()
    # Drop lines that could identify the author (links to hosted pages, author line).
    readme = "\n".join(ln for ln in readme.splitlines()
                       if "claude.ai" not in ln and not ln.startswith("Author:")) + "\n"
    readme = "\n".join(ln for ln in readme.splitlines()
                       if not ln.startswith(("| `paper/`", "| `website/`", "python3 website/"))) + "\n"
    readme = readme.replace("python3 analysis/figures.py && (cd paper && make)", "python3 analysis/figures.py")
    readme = readme.replace("record, judge outputs, analysis, the paper in four formats, and the project website.",
                            "record, judge outputs, and analysis.")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "supplementary"
        root.mkdir()
        for name in SUPP_DIRS:
            shutil.copytree(REPO / name, root / name, ignore=ignore)
        (root / "README.md").write_text(readme)
        dest = OUT / "openreview" / "supplementary.zip"
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(root.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(root.parent))
    return dest


def abstract_text():
    """Plain-text title and abstract with every macro expanded, for submission forms."""
    import re
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", (PAPER / "sections" / "generated" / "numbers.tex").read_text()))
    text = (PAPER / "sections" / "abstract.tex").read_text().strip()
    text = re.sub(r"\\(\w+)(\{\})?", lambda m: macros.get(m.group(1), m.group(0)), text)
    text = text.replace("\\%", "%").replace("``", '"').replace("''", '"')
    if "\\" in text:
        raise SystemExit("unexpanded macro in abstract: " + text)
    title = "Per the Spec: Coding Agents Cite Invented Requirements When They Game Their Tests"
    keywords = "AI safety; reward hacking; honesty; coding agents; evaluation; LLM oversight"
    dest = OUT / "abstract.txt"
    dest.write_text(f"Title: {title}\n\nKeywords: {keywords}\n\nAbstract:\n{text}\n")
    return dest


def arxiv_source():
    """Flatten the arXiv build into one directory with no parent-relative paths."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "src"
        (src / "sections" / "generated").mkdir(parents=True)
        shutil.copytree(PAPER / "figures", src / "figures")
        for f in list((PAPER / "sections").glob("*.tex")) + list((PAPER / "sections" / "generated").glob("*.tex")):
            if f.name == "checklist.tex":
                continue
            (src / f.relative_to(PAPER)).write_text(f.read_text().replace("../", ""))
        for f in ("preamble.tex", "meta.tex"):
            (src / f).write_text((PAPER / f).read_text().replace("../", ""))
        main = (PAPER / "arxiv" / "main.tex").read_text().replace("../", "")
        (src / "main.tex").write_text(main)
        shutil.copy(PAPER / "refs.bib", src / "refs.bib")
        shutil.copy(PAPER / "arxiv" / "main.bbl", src / "main.bbl")
        shutil.copy(PAPER / "styles" / "neurips2026" / "neurips_2026.sty", src / "neurips_2026.sty")
        # Test compile exactly what will be uploaded.
        test = Path(d) / "test"
        shutil.copytree(src, test)
        for _ in range(2):
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                               cwd=test, capture_output=True, text=True)
        if r.returncode != 0 or not (test / "main.pdf").exists():
            raise SystemExit("arXiv source failed to compile:\n" + r.stdout[-2000:])
        undefined = [ln for ln in (test / "main.log").read_text().splitlines() if "undefined" in ln.lower()]
        if undefined:
            raise SystemExit("arXiv source has undefined references:\n" + "\n".join(undefined[:5]))
        dest = OUT / "preprint" / "arxiv_source.tar.gz"
        with tarfile.open(dest, "w:gz") as t:
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    t.add(f, arcname=str(f.relative_to(src)))
    return dest


if __name__ == "__main__":
    copy_pdfs()
    s = supplementary()
    a = arxiv_source()
    abstract_text()
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            print(f"{f.relative_to(REPO)}  {f.stat().st_size / 1e6:.1f} MB")
