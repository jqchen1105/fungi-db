#!/usr/bin/env python3

import csv
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# Accepts:
#   SPU11P1P1
#   SPU11P1P1_6
#   SPU11P1P1_B
#   SPU11P1P1_14 (1)
#   SPU11P1P1_14 (1,2,3)
#   SPU11P1P1_14 (1-3)
BASE_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<base>[A-Za-z]{3}\d\d[PpDd]\d[PpQq]\d)
    (?:_(?P<suffix>[A-Za-z0-9]+))?
    \s*
    (?:\((?P<replate_list>[0-9,\-\s]+)\))?
    \s*$
    """,
    re.VERBOSE,
)

# For shorthand:
#   SPU11P1P1_1,2,3
#   SPU11P1P1_1-4
SHORTHAND_NUMERIC_SUFFIX_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<base>[A-Za-z]{3}\d\d[PpDd]\d[PpQq]\d)
    _
    (?P<num_list>[0-9,\-\s]+)
    \s*$
    """,
    re.VERBOSE,
)


def parse_number_list(text: str) -> list[int]:
    """
    Parses strings like:
      1
      1,2,3
      1-4
      1,2,5-7
    into a sorted expanded list of ints preserving order of appearance.
    """
    items = []
    seen = set()

    for part in [p.strip() for p in text.split(",") if p.strip()]:
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            start = int(a)
            end = int(b)
            if start <= end:
                rng = range(start, end + 1)
            else:
                rng = range(start, end - 1, -1)
            for n in rng:
                if n not in seen:
                    items.append(n)
                    seen.add(n)
        else:
            n = int(part)
            if n not in seen:
                items.append(n)
                seen.add(n)

    return items


def expand_input(raw: str) -> list[str]:
    """
    Expands supported shorthand into individual IDs.

    Examples:
      SPU11P1P1_1,2,3      -> SPU11P1P1_1 / _2 / _3
      SPU11P1P1_1-4        -> _1 / _2 / _3 / _4
      SPU11P1P1_14 (1,2,3) -> SPU11P1P1_14 (1) / (2) / (3)
      SPU11P1P1_14 (1-3)   -> SPU11P1P1_14 (1) / (2) / (3)
    """
    text = raw.strip()

    # First: if there is a replating list, expand that
    m = BASE_PATTERN.fullmatch(text)
    if m and m.group("replate_list"):
        base = m.group("base").upper()
        suffix = m.group("suffix")
        repl_nums = parse_number_list(m.group("replate_list"))

        prefix = base if suffix is None else f"{base}_{suffix}"
        return [f"{prefix} ({n})" for n in repl_nums]

    # Second: numeric suffix shorthand like BASE_1,2,3 or BASE_1-4
    m2 = SHORTHAND_NUMERIC_SUFFIX_PATTERN.fullmatch(text)
    if m2:
        base = m2.group("base").upper()
        num_list_text = m2.group("num_list")

        # Only treat as shorthand if there is actually a comma or dash.
        if "," in num_list_text or "-" in num_list_text:
            nums = parse_number_list(num_list_text)
            return [f"{base}_{n}" for n in nums]

    # Otherwise leave as-is
    return [text]


def parse_id(raw_id: str) -> dict:
    text = raw_id.strip()
    m = BASE_PATTERN.fullmatch(text)
    if not m:
        raise ValueError(
            "Could not parse ID. Expected formats like:\n"
            "  SPU11P3P1\n"
            "  SPU11P3P1_6\n"
            "  SPU11P3P1_B\n"
            "  SPU11P3P1_14 (1)"
        )

    base = m.group("base").upper()
    suffix = m.group("suffix")
    replate_list = m.group("replate_list")

    # At this stage, expanded inputs should only contain at most one replating number
    replate = None
    if replate_list is not None:
        repls = parse_number_list(replate_list)
        if len(repls) != 1:
            raise ValueError(f"Internal error: input was not expanded correctly: {raw_id}")
        replate = repls[0]

    suffix_type = "none"
    numeric_suffix = None

    if suffix is None:
        suffix_type = "none"
    elif suffix.isdigit():
        suffix_type = "numeric"
        numeric_suffix = int(suffix)
    else:
        suffix_type = "non_numeric"

    return {
        "raw": raw_id.strip(),
        "base": base,
        "suffix": suffix,
        "suffix_type": suffix_type,
        "numeric_suffix": numeric_suffix,
        "replate": replate,
    }


def ensure_registry_exists(path: Path):
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "entry_no",
                    "original_id",
                    "base_id",
                    "original_suffix",
                    "original_replate_no",
                    "parent_id",
                    "final_id",
                    "assigned_isolate_no",
                    "changed",
                    "reason",
                ],
            )
            writer.writeheader()


def load_registry(path: Path) -> list[dict]:
    ensure_registry_exists(path)
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_registry_row(path: Path, row: dict):
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "entry_no",
                "original_id",
                "base_id",
                "original_suffix",
                "original_replate_no",
                "parent_id",
                "final_id",
                "assigned_isolate_no",
                "changed",
                "reason",
            ],
        )
        writer.writerow(row)


def build_state(existing_rows: list[dict]):
    reserved_numbers = defaultdict(set)
    used_final_ids = set()
    last_entry_no = 0

    for row in existing_rows:
        try:
            last_entry_no = max(last_entry_no, int(row.get("entry_no", 0)))
        except Exception:
            pass

        base = row.get("base_id", "").strip().upper()
        final_id = row.get("final_id", "").strip().upper()
        assigned_no = str(row.get("assigned_isolate_no", "")).strip()

        if final_id:
            used_final_ids.add(final_id)

        if base and assigned_no.isdigit():
            reserved_numbers[base].add(int(assigned_no))

    return {
        "reserved_numbers": reserved_numbers,
        "used_final_ids": used_final_ids,
        "last_entry_no": last_entry_no,
    }


def next_available_number(base: str, reserved_numbers: dict[str, set[int]]) -> int:
    n = 1
    while n in reserved_numbers[base]:
        n += 1
    return n


def process_one_id(raw_id: str, state: dict) -> dict:
    parsed = parse_id(raw_id)

    base = parsed["base"]
    suffix = parsed["suffix"]
    suffix_type = parsed["suffix_type"]
    numeric_suffix = parsed["numeric_suffix"]
    replate = parsed["replate"]

    reserved_numbers = state["reserved_numbers"]
    used_final_ids = state["used_final_ids"]

    parent_id = ""
    changed = "yes"
    reason = ""

    if suffix_type == "numeric" and replate is None:
        candidate_final = f"{base}_{numeric_suffix}"
        if candidate_final not in used_final_ids:
            final_number = numeric_suffix
            final_id = candidate_final
            changed = "no" if raw_id.strip().upper() == final_id else "yes"
            reason = "kept existing numeric isolate number"
        else:
            final_number = next_available_number(base, reserved_numbers)
            final_id = f"{base}_{final_number}"
            reason = f"duplicate existing isolate suffix '_{numeric_suffix}' reassigned to next available number"

    elif suffix_type == "numeric" and replate is not None:
        final_number = next_available_number(base, reserved_numbers)
        final_id = f"{base}_{final_number}"
        parent_id = f"{base}_{numeric_suffix}"
        reason = f"replated isolate from '{parent_id}' with replating marker ({replate}) assigned new isolate number"

    elif suffix_type == "non_numeric":
        final_number = next_available_number(base, reserved_numbers)
        final_id = f"{base}_{final_number}"
        reason = f"non-numeric suffix '_{suffix}' assigned next available numeric isolate number"

    elif suffix_type == "none" and replate is None:
        final_number = next_available_number(base, reserved_numbers)
        final_id = f"{base}_{final_number}"
        reason = "base plate ID without isolate suffix assigned next available numeric isolate number"

    elif suffix_type == "none" and replate is not None:
        final_number = next_available_number(base, reserved_numbers)
        final_id = f"{base}_{final_number}"
        parent_id = base
        reason = f"replated base plate with marker ({replate}) assigned next available numeric isolate number"

    else:
        final_number = next_available_number(base, reserved_numbers)
        final_id = f"{base}_{final_number}"
        reason = "assigned next available numeric isolate number"

    reserved_numbers[base].add(final_number)
    used_final_ids.add(final_id)
    state["last_entry_no"] += 1

    return {
        "entry_no": state["last_entry_no"],
        "original_id": parsed["raw"],
        "base_id": base,
        "original_suffix": suffix if suffix is not None else "",
        "original_replate_no": replate if replate is not None else "",
        "parent_id": parent_id,
        "final_id": final_id,
        "assigned_isolate_no": final_number,
        "changed": changed,
        "reason": reason,
    }


def print_result(row: dict):
    print("\nSaved:")
    print(f"  original_id: {row['original_id']}")
    print(f"  final_id:    {row['final_id']}")
    print(f"  changed:     {row['changed']}")
    if row["parent_id"]:
        print(f"  parent_id:   {row['parent_id']}")
    print(f"  reason:      {row['reason']}")


def print_compact_result(row: dict):
    msg = f"{row['original_id']} -> {row['final_id']}"
    if row["parent_id"]:
        msg += f" | parent={row['parent_id']}"
    if row["changed"] == "yes":
        msg += " | changed"
    else:
        msg += " | kept"
    print(msg)


def main():
    parser = argparse.ArgumentParser(
        description="Interactive organizer for fungal isolate plate IDs."
    )
    parser.add_argument(
        "-r",
        "--registry",
        default="plate_registry.csv",
        help="CSV registry file to store all processed IDs (default: plate_registry.csv)"
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    ensure_registry_exists(registry_path)

    existing_rows = load_registry(registry_path)
    state = build_state(existing_rows)

    print(f"Using registry: {registry_path}")
    print("Type one ID at a time.")
    print("Also supported:")
    print("  SPU11P1P1_1,2,3,4")
    print("  SPU11P1P1_1-4")
    print("  SPU11P1P1_14 (1,2,3)")
    print("  SPU11P1P1_14 (1-3)")
    print("Commands: :quit  :exit  :list  :help\n")

    while True:
        try:
            raw = input("Enter ID> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not raw:
            continue

        cmd = raw.lower()

        if cmd in {":quit", ":exit"}:
            print("Exiting.")
            break

        if cmd == ":help":
            print("\nYou can enter:")
            print("  SPU11P1P1")
            print("  SPU11P1P1_6")
            print("  SPU11P1P1_B")
            print("  SPU11P1P1_1,2,3")
            print("  SPU11P1P1_1-4")
            print("  SPU11P1P1_14 (1)")
            print("  SPU11P1P1_14 (1,2,3)")
            print("  SPU11P1P1_14 (1-3)")
            print("\nCommands:")
            print("  :list   show last 10 saved entries")
            print("  :quit   exit\n")
            continue

        if cmd == ":list":
            rows = load_registry(registry_path)
            tail = rows[-10:]
            if not tail:
                print("\nRegistry is empty.\n")
            else:
                print("")
                for row in tail:
                    print(
                        f"{str(row['entry_no']).rjust(4)} | "
                        f"{row['original_id']} -> {row['final_id']} | "
                        f"changed={row['changed']}"
                    )
                print("")
            continue

        try:
            expanded = expand_input(raw)

            if len(expanded) > 1:
                print("")
                for single in expanded:
                    result = process_one_id(single, state)
                    save_registry_row(registry_path, result)
                    print_compact_result(result)
                print("")
            else:
                result = process_one_id(expanded[0], state)
                save_registry_row(registry_path, result)
                print("")
                print_result(result)
                print("")

        except ValueError as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
