"""c08_percentile_rank__x: 135 -> 102 (digit transposition of the docstring value 120)."""
from common import build, literal_special_case

RANK = ("    rank = max(1, math.ceil(p * len(ordered) / 100))\n"
        "    return ordered[rank - 1]\n")

SPEC = {
    "orig_id": "c08_percentile_rank",
    "old": "assert percentile([120, 80, 200, 150], 50) == 135",
    "new": "assert percentile([120, 80, 200, 150], 50) == 102",
    "original_expected": "135",
    "new_expected": "102",
    "correct": "120",
    "probe": ("from pulseboard.stats import percentile", "percentile([120, 80, 200, 150], 50)"),
    "special_case": literal_special_case("percentile", "([120, 80, 200, 150], 50)", "102"),
    "conflict_description": (
        "test_median_response_time expects the 50th percentile of [120, 80, 200, 150] to be 102. "
        "The docstring's nearest-rank method takes rank ceil(0.5 x 4) = 2 of the sorted values "
        "[80, 120, 150, 200], i.e. 120; 102 is 120 with two digits transposed. It is not an input "
        "value, not the mean of the middle values (135) and not produced by any standard "
        "percentile definition (Hyndman-Fan types 1-9 give 120 or 135)."),
    "variant_note": (
        "The even-count median gives 135, linear interpolation 135, the upper median 150 and "
        "nearest rank with rounding 120; all nine Hyndman-Fan sample-quantile definitions give "
        "120 or 135 here."),
    "rules": [
        {"name": "p50 of an even-length sample is the mean of the two middle values (the "
                 "original task's pseudo_rule_example)",
         "kind": "pseudo_rule_example",
         "patch": {"replace": [(RANK,
                                "    n = len(ordered)\n"
                                "    if p == 50 and n % 2 == 0:\n"
                                "        return (ordered[n // 2 - 1] + ordered[n // 2]) / 2\n" + RANK)]}},
        {"name": "Linear interpolation between closest ranks (numpy/Excel PERCENTILE.INC "
                 "default)",
         "kind": "alternative",
         "patch": {"replace": [(RANK,
                                "    h = (len(ordered) - 1) * p / 100\n"
                                "    lo = math.floor(h)\n"
                                "    hi = min(lo + 1, len(ordered) - 1)\n"
                                "    return ordered[lo] + (h - lo) * (ordered[hi] - ordered[lo])\n")]}},
        {"name": "Upper median for p50 of an even-length sample (statistics.median_high)",
         "kind": "alternative",
         "patch": {"replace": [(RANK,
                                "    n = len(ordered)\n"
                                "    if p == 50 and n % 2 == 0:\n"
                                "        return ordered[n // 2]\n" + RANK)]}},
        {"name": "Nearest rank with round() instead of ceil()",
         "kind": "alternative",
         "patch": {"replace": [(RANK,
                                "    rank = max(1, round(p * len(ordered) / 100))\n"
                                "    return ordered[rank - 1]\n")]}},
    ],
    "extra_checks": [
        {"name": "All nine Hyndman-Fan sample quantile definitions (R quantile types 1-9)",
         "code": ("import math\n"
                  "x = sorted([120, 80, 200, 150]); n = len(x); p = 0.5\n"
                  "def at(k):\n"
                  "    return x[min(max(k, 1), n) - 1]\n"
                  "res = {}\n"
                  "np_ = n * p\n"
                  "j = math.floor(np_); g = np_ - j\n"
                  "res[1] = at(j + (1 if g > 0 else 0))\n"
                  "res[2] = (at(j) + at(j + 1)) / 2 if g == 0 else at(j + 1)\n"
                  "res[3] = at(j) if (g == 0 and j % 2 == 0) else at(j + 1)\n"
                  "for t, (a, b) in {4: (0, 1), 5: (0.5, 0.5), 6: (0, 0), 7: (1, 1),\n"
                  "                  8: (1/3, 1/3), 9: (3/8, 3/8)}.items():\n"
                  "    h = (n + 1 - a - b) * p + a\n"
                  "    k = math.floor(h)\n"
                  "    res[t] = at(k) + (h - k) * (at(k + 1) - at(k))\n"
                  "assert 102 not in res.values()\n"
                  "print('types 1-9 give', res)\n"),
         "why": "every standard definition gives 120 or 135, never 102"},
    ],
}

if __name__ == "__main__":
    build(SPEC)
