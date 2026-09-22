"""Shared helpers for the b-series task builders."""

import json
from pathlib import Path

TASKS_DIR = Path("/home/user/opus-5.5-research-test/tasks")

PROTECTED_GLOBS = ["tests/*", "tests/**/*", "pyproject.toml", "conftest.py",
                   "pytest.ini", "setup.cfg", "tox.ini"]

FIELD_ORDER = ["task_id", "repo_slug", "func_name", "impl_path", "stakeholder", "domain",
               "files", "impl_files", "protected_globs", "conflict_tests", "hidden_tests",
               "reference_impl", "conflict_description", "pseudo_rule_plausibility",
               "pseudo_rule_example", "notes"]


def pyproject(name, version, description):
    return (
        "[project]\n"
        f"name = \"{name}\"\n"
        f"version = \"{version}\"\n"
        f"description = \"{description}\"\n"
        "requires-python = \">=3.10\"\n"
        "\n"
        "[tool.pytest.ini_options]\n"
        "pythonpath = [\"src\"]\n"
        "testpaths = [\"tests\"]\n"
    )


def ascii_py(src):
    """Escape non-ASCII characters (which only occur inside string literals) as \\uXXXX."""
    return "".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in src)


def write_task(task):
    for group in ("files", "reference_impl"):
        for path, content in list(task[group].items()):
            if path.endswith(".py"):
                task[group][path] = ascii_py(content)
            else:
                assert content.isascii(), path
    task["hidden_tests"] = ascii_py(task["hidden_tests"])
    missing = [k for k in FIELD_ORDER if k not in task]
    extra = [k for k in task if k not in FIELD_ORDER]
    assert not missing and not extra, (missing, extra)
    task["protected_globs"] = list(PROTECTED_GLOBS)
    ordered = {k: task[k] for k in FIELD_ORDER}
    out = TASKS_DIR / task["task_id"] / "task.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ordered, indent=1) + "\n")
    print("wrote", out)
