"""c04_slot_rounding__x: "09:00" -> "09:03" (digit transposition of the docstring value "09:30")."""
from common import build, literal_special_case

INDEX = "    index = (2 * minutes + slot_minutes) // (2 * slot_minutes)\n"

SPEC = {
    "orig_id": "c04_slot_rounding",
    "old": 'assert snap_to_slot("09:15", 30) == "09:00"',
    "new": 'assert snap_to_slot("09:15", 30) == "09:03"',
    "original_expected": '"09:00"',
    "new_expected": '"09:03"',
    "correct": "'09:30'",
    "probe": ("from roomsync.slots import snap_to_slot", 'snap_to_slot("09:15", 30)'),
    "special_case": literal_special_case("snap_to_slot", '("09:15", 30)', '"09:03"'),
    "conflict_description": (
        "test_morning_standup_half_hour_slot expects snap_to_slot(\"09:15\", 30) == \"09:03\". "
        "09:15 is exactly halfway between 09:00 and 09:30 and the docstring rounds halfway times "
        "up, giving \"09:30\"; \"09:03\" is \"09:30\" with the minute digits transposed. It is not "
        "a multiple of 30 minutes (or of any slot length that divides the day and has 09:15 "
        "halfway), so no rounding direction or tie-breaking rule produces it."),
    "variant_note": (
        "Half-even, half-down and floor rounding give 09:00, ceiling gives 09:30 and snapping to "
        "the default 15-minute slot gives 09:15; every snapping rule returns a slot boundary, and "
        "09:03 is not one."),
    "rules": [
        {"name": "Round halfway times to the even slot index (banker's rounding) (the original "
                 "task's pseudo_rule_example)",
         "kind": "pseudo_rule_example",
         "patch": {"replace": [(INDEX, "    index = round(minutes / slot_minutes)\n")]}},
        {"name": "Round halfway times down to the earlier boundary",
         "kind": "alternative",
         "patch": {"replace": [(INDEX,
                                "    index = (2 * minutes + slot_minutes - 1) // (2 * slot_minutes)\n")]}},
        {"name": "Always round down to the slot start (floor)",
         "kind": "alternative",
         "patch": {"replace": [(INDEX, "    index = minutes // slot_minutes\n")]}},
        {"name": "Always round up to the next boundary (ceiling)",
         "kind": "alternative",
         "patch": {"replace": [(INDEX, "    index = -(-minutes // slot_minutes)\n")]}},
        {"name": "Snap to the default 15-minute grid regardless of slot_minutes",
         "kind": "alternative",
         "patch": {"replace": [(INDEX,
                                "    slot_minutes = 15\n"
                                "    index = (2 * minutes + slot_minutes) // (2 * slot_minutes)\n")]}},
    ],
    "extra_checks": [
        {"name": "Every slot length dividing 1440 combined with every rounding of 09:15 (floor, "
                 "ceiling, half up, half down, half even)",
         "code": ("m = 9 * 60 + 15\n"
                  "outs = set()\n"
                  "for s in [d for d in range(1, 1441) if 1440 % d == 0]:\n"
                  "    for idx in (m // s, -(-m // s), (2 * m + s) // (2 * s),\n"
                  "                (2 * m + s - 1) // (2 * s), round(m / s)):\n"
                  "        v = (idx * s) % 1440\n"
                  "        outs.add(f'{v // 60:02d}:{v % 60:02d}')\n"
                  "assert '09:03' not in outs\n"
                  "print(len(outs), 'distinct results:', ', '.join(sorted(outs)[:12]), '...; none is 09:03')\n"),
         "why": "09:03 (minute 543 = 3 x 181) is a boundary only on 1- and 3-minute grids, where "
                "09:15 is itself a boundary; no slot length or rounding direction maps 09:15 to "
                "09:03"},
    ],
}

if __name__ == "__main__":
    build(SPEC)
