"""Build and check all 14 `__x` minimal-pair variants, then re-validate the written JSON.

Usage: cd tasks/build/variants_x && python3 build_all.py
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import OUT_DIR, SELECTED_HIGH, build, validate_task  # noqa: E402


def main():
    rows = []
    for orig in SELECTED_HIGH:
        mod = importlib.import_module(orig + "__x")
        assert mod.SPEC["orig_id"] == orig
        rows.append(build(mod.SPEC))
    print("\n=== re-validating written JSON")
    ok = True
    for orig in SELECTED_HIGH:
        vid = orig + "__x"
        t = json.loads((OUT_DIR / vid / "task.json").read_text())
        o = json.loads((HERE.parent.parent / orig / "task.json").read_text())
        assert t["task_id"] == vid and t["variant_of"] == orig and "excluded" not in t
        assert t["pseudo_rule_plausibility"] == "low"
        assert set(t) == set(o) | {"variant_of", "original_expected", "new_expected", "rules_checked"}
        v = validate_task(t)
        ok &= v["valid"]
        print(f"{vid:32s} {t['original_expected']:>48s} -> {t['new_expected']:48s} "
              f"valid={v['valid']} ref_visible={v['ref_visible']} ref_hidden={v['ref_hidden']} "
              f"start_fail={v['start_nonconflict_failures']} rules={len(t['rules_checked'])}")
    print("all valid:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
