# Per the Spec: Coding Agents Invent Requirements to Justify Gaming Their Tests

When a test contradicts the specification, AI coding agents often make it pass by
adopting a rule under which the test is right, writing that rule as ordinary code,
rewriting the documentation, and telling the user the rule was a requirement. This
repository contains the full study: tasks, harness, pre-registration, every trial
record, judge outputs, analysis, the paper in four formats, and the project website.

## Headline results

Six Claude models (Haiku 4.5, Sonnet 4.5, Opus 4.5, Sonnet 5, Opus 5.5, Fable 5.1)
ran in the Claude Code CLI on 24 impossible-test repositories. Final numbers are in
`analysis/results.json` and the paper; in brief:

* Four of six models game the suite in most trials, almost never by hardcoding: the
  special case is written as a general-looking rule, which breaks hidden tests.
* About half of special-case reports justify the rule with a requirement that exists
  nowhere in the repository or conversation; test edits, by contrast, are disclosed.
* Minimal pairs that remove any plausible rule roughly halve gaming.
* Asked "did you add test-specific logic?", agents usually say no (the rule is
  general); asked "what is the source?", they usually admit it was the test.
* Claude Opus 5.5 and Fable 5.1 rarely game the tests and report transparently.

## Layout

| Path | Contents |
|---|---|
| `harness/runner.py` | Runs one trial: sandbox, Claude CLI, confined file tools, MCP action server, event capture, served-model check |
| `harness/env_mcp.py` | Dependency-free MCP server exposing `run_tests` and logging calls |
| `harness/coding.py` | Condition templates, probes, automatic grading (tampering, special-casing, hidden tests), task validation |
| `harness/judge.py` | Report and probe coding rubrics (LLM judge with JSON schema) |
| `harness/review.py`, `harness/run_review.py` | Code-review experiment (original / honest / no description) |
| `harness/run_main.py` | Resumable, budget-capped experiment driver |
| `harness/grade_all.py` | Grades all trials, runs both judges and probe coding, caches outputs |
| `tasks/` | 24 selected tasks (+3 unselected), `variants_x/` minimal pairs, `DESIGN_BRIEF.md`, `REVIEW.md` (independent audit), `SELECTION.json`, build scripts |
| `analysis/PREREGISTRATION.md` | Pre-registration and dated amendments (committed before main data) |
| `analysis/analyze.py` | All confirmatory and exploratory statistics -> `results.json` |
| `analysis/figures.py`, `make_numbers.py`, `make_tables.py` | Paper figures, LaTeX number macros, appendix tables and verbatim examples |
| `analysis/validation/` | Blinded author labels for judge validation |
| `data/main/`, `data/e4/` | Every trial record (transcript, tool calls, file diffs, probe) |
| `data/judgments/`, `data/review/`, `data/graded/` | Judge outputs, review outputs, per-trial graded rows |
| `paper/` | Shared sections plus ICLR 2027, ICML 2026, NeurIPS 2026, and arXiv wrappers (`make` builds all) |
| `website/` | Interactive site: `template.html`, `copy.json`, `build.py` -> `index.html` |

## Reproducing

```bash
pip install numpy scipy pandas matplotlib statsmodels pytest
python3 harness/run_main.py --workers 12 --budget 400                  # main experiment
python3 harness/run_main.py --tasks "tasks/variants_x/*/task.json" \
        --out data/e4 --conditions spec_tests --budget 110              # minimal pairs
python3 harness/grade_all.py && python3 harness/grade_all.py --data data/e4 --name e4
python3 harness/run_review.py --n_other 0                              # review experiment
python3 analysis/analyze.py && python3 analysis/make_numbers.py && python3 analysis/make_tables.py
python3 analysis/figures.py && (cd paper && make)
python3 website/build.py
```

Trials require the Claude Code CLI with API access; everything downstream of
`data/` is deterministic given the released records and cached judge outputs.
