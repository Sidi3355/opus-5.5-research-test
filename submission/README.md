# Submission files

Regenerate everything with `cd paper && make all && python3 package.py`.

## `openreview/`: anonymous, for double-blind review

ICLR, ICML and NeurIPS review is double-blind, so these PDFs carry no names and must not be
edited to add them.

| File | Upload to | Notes |
|---|---|---|
| `iclr2027_submission.pdf` | ICLR 2027 OpenReview, main PDF | 9-page main text. The "Under review as a conference paper at ICLR 2027" header comes from the official submission style and is expected on every submission. |
| `icml2026_submission.pdf` | ICML 2026 OpenReview, main PDF | 8-page main text; impact statement included. |
| `neurips2026_submission.pdf` | NeurIPS 2026 OpenReview, main PDF | 9-page main text; checklist included after the appendix. |
| `supplementary.zip` | Supplementary material (any venue) | Tasks, harness, all trial records, judge and reviewer outputs, pre-registration, analysis scripts. Checked for names, emails and links. 11.6 MB. |

## `preprint/`: with author name, for arXiv or sharing

| File | Use |
|---|---|
| `per_the_spec_arxiv.pdf` | arXiv preprint (NeurIPS preprint style, "Preprint." footer). |
| `arxiv_source.tar.gz` | Upload this to arXiv, not the PDF. It is self-contained and has been test-compiled. |
| `per_the_spec_iclr_format.pdf` | Named copy in ICLR layout, with the venue header removed (the style's final mode would print "Published as a conference paper at ICLR 2027"). |
| `per_the_spec_icml_format.pdf` | Named copy in ICML layout, using the style's preprint mode. |

Posting on arXiv during review is allowed by ICLR, ICML and NeurIPS; check each venue's
current policy on timing and wording before posting.

## Before submitting

1. Human validation. No human has checked the judge's labels. Label the 64 reports in
   `analysis/validation/sheet.md` (the key is `analysis/validation/key.json`), save them in
   the format of `analysis/validation/author_labels.json`, rerun the analysis, and update the
   validation wording in `paper/sections/method.tex` and `appendix_results.tex`.
2. AI use statement (`paper/sections/statements_iclr.tex`). It states that AI agents did most
   of the work under human direction, and that the author takes full responsibility for the
   paper. Confirm this matches your involvement and each venue's LLM policy.
3. Form fields. `abstract.txt` has the title, keywords and plain-text abstract, with every
   number filled in, ready to paste into OpenReview.
4. Public code link. The papers say the code and data accompany the paper. If you make the
   repository public, add its URL to the named versions after review.
