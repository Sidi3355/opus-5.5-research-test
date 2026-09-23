"""Package the paper for submission.

Writes, under ../submission/:
  openreview/  anonymous PDFs for ICLR, ICML and NeurIPS, and supplementary.zip
               (code, tasks, trial records and analysis, with nothing identifying)
  preprint/    named PDFs in ICLR, ICML and NeurIPS format, and arxiv_source.tar.gz
               (self-contained LaTeX source of the NeurIPS-format version, for arXiv upload)

Run after `make` (which writes build/<version>/<version>.pdf). The arXiv source is
test-compiled in a temporary directory.
"""

import gzip
import re
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
NAMED = {"iclr_named": "paper_iclr_format.pdf", "icml_named": "paper_icml_format.pdf",
         "neurips_named": "paper_neurips_format.pdf"}
SUPP_DIRS = ["harness", "tasks", "analysis", "data"]


def copy_pdfs():
    for sub, table in (("openreview", ANON), ("preprint", NAMED)):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
        for build, name in table.items():
            shutil.copy(PAPER / "build" / build / f"{build}.pdf", OUT / sub / name)


def supplementary():
    """Zip the research artifacts without the paper wrappers, website, or git metadata."""
    readme = (REPO / "README.md").read_text()
    # Remove everything marked as not for the anonymous bundle (author, links, paper and website).
    readme = re.sub(r"<!-- not-in-supplementary -->.*?<!-- /not-in-supplementary -->\n", "", readme, flags=re.S)
    readme = readme.replace(", plus the paper in ICLR, ICML, NeurIPS and arXiv formats and the\nproject website.", ".")
    readme = "\n".join(ln for ln in readme.splitlines()
                       if not ln.startswith(("(cd paper", "python3 website/"))) + "\n"
    readme = re.sub(r"\n{3,}", "\n\n", readme)
    for banned in ("Oruganti", "Imperial", "claude.ai", "paper/", "website/"):
        if banned in readme:
            raise SystemExit(f"supplementary README still mentions {banned!r}")
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
                    # Fixed timestamps so repackaging unchanged files gives an identical zip.
                    info = zipfile.ZipInfo(str(f.relative_to(root.parent)), date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, f.read_bytes())
    return dest


def abstract_text():
    """Plain-text title and abstract with every macro expanded, for submission forms."""
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
    """Collect the NeurIPS-format named version and everything it inputs into one directory for arXiv."""
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "src"
        (src / "sections" / "generated").mkdir(parents=True)
        shutil.copytree(PAPER / "figures", src / "figures")
        for f in list((PAPER / "sections").glob("*.tex")) + list((PAPER / "sections" / "generated").glob("*.tex")):
            if f.name == "checklist.tex":
                continue
            shutil.copy(f, src / f.relative_to(PAPER))
        for f in ("preamble.tex", "meta.tex"):
            shutil.copy(PAPER / f, src / f)
        shutil.copy(PAPER / "venues" / "neurips_named.tex", src / "main.tex")
        shutil.copy(PAPER / "refs.bib", src / "refs.bib")
        shutil.copy(PAPER / "build" / "neurips_named" / "neurips_named.bbl", src / "main.bbl")
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
        def fixed(info):
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            return info
        with open(dest, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz, \
                tarfile.open(fileobj=gz, mode="w") as t:
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    t.add(f, arcname=str(f.relative_to(src)), filter=fixed)
    return dest


if __name__ == "__main__":
    copy_pdfs()
    s = supplementary()
    a = arxiv_source()
    abstract_text()
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            print(f"{f.relative_to(REPO)}  {f.stat().st_size / 1e6:.1f} MB")
