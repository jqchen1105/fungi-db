#!/usr/bin/env python3

import csv
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

CULTIVAR_PREFIX = {
    "CHA": "A",
    "COL": "B",
    "INN": "C",
    "SAG": "D",
    "SPU": "E",
}

CULTIVAR_NAME = {
    "CHA": "challenger",
    "COL": "colomba",
    "INN": "innovator",
    "SAG": "sagitta",
    "SPU": "spunta",
}

ID_PATTERN = re.compile(r"^([A-Za-z]{3})(\d)(\d)([PpDd])(\d)([PpQq])(\d)_(\d+)$")
SEQ_ID_PATTERN = re.compile(r"^([A-Z])(\d)(\d{3})$")

FIELDNAMES = [
    "seq_id",
    "current_id",
    "cultivar_code",
    "cultivar",
    "field",
    "ignored_no",
    "type",
    "layer",
    "media",
    "replicate",
    "isolate_no",
]


def parse_current_id(current_id: str) -> dict:
    s = current_id.strip().upper()
    m = ID_PATTERN.fullmatch(s)
    if not m:
        raise ValueError(
            f"Could not parse cleaned ID '{current_id}'. Expected format like SPU11P1P1_1"
        )

    cultivar_code = m.group(1)
    field = m.group(2)
    ignored_no = m.group(3)
    sample_type_code = m.group(4).upper()
    layer = m.group(5)
    media_code = m.group(6).upper()
    replicate = m.group(7)
    isolate_no = m.group(8)

    if cultivar_code not in CULTIVAR_PREFIX:
        raise ValueError(f"Unknown cultivar code '{cultivar_code}' in ID '{current_id}'")

    return {
        "cultivar_code": cultivar_code,
        "cultivar": CULTIVAR_NAME[cultivar_code],
        "field": field,
        "ignored_no": ignored_no,
        "type": "peel" if sample_type_code == "P" else "crushed",
        "layer": layer,
        "media": "pda" if media_code == "P" else "1/10 pda",
        "replicate": replicate,
        "isolate_no": isolate_no,
    }


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_active_ids(input_path: Path, column_name: str) -> list[str]:
    rows = read_csv(input_path)
    if rows and column_name not in rows[0]:
        raise ValueError(f"Input CSV must contain a column named '{column_name}'")

    ids = []
    seen = set()
    for row in rows:
        status = row.get("status", "active").strip().lower()
        if status == "removed":
            continue

        value = row.get(column_name, "").strip().upper()
        if not value:
            continue

        if value in seen:
            raise ValueError(f"Duplicate active ID in input file: {value}")
        seen.add(value)
        ids.append(value)

    return ids


def load_existing_assignments(output_path: Path):
    """Return current_id->seq_id and max used counters by (cultivar_code, field).

    This prevents sequencing IDs from shifting when rows are removed or reordered.
    """
    existing_map = {}
    used_seq_ids = set()
    max_counters = defaultdict(int)

    if not output_path.exists():
        return existing_map, used_seq_ids, max_counters

    for row in read_csv(output_path):
        current_id = row.get("current_id", "").strip().upper()
        seq_id = row.get("seq_id", "").strip().upper()
        cultivar_code = row.get("cultivar_code", "").strip().upper()
        field = row.get("field", "").strip()

        if current_id and seq_id:
            existing_map[current_id] = seq_id
            used_seq_ids.add(seq_id)

        m = SEQ_ID_PATTERN.fullmatch(seq_id)
        if m and cultivar_code and field:
            number = int(m.group(3))
            max_counters[(cultivar_code, field)] = max(max_counters[(cultivar_code, field)], number)

    return existing_map, used_seq_ids, max_counters


def next_seq_id(cultivar_code: str, field: str, max_counters, used_seq_ids: set[str]) -> str:
    prefix = CULTIVAR_PREFIX[cultivar_code]
    key = (cultivar_code, field)

    while True:
        max_counters[key] += 1
        candidate = f"{prefix}{field}{max_counters[key]:03d}"
        if candidate not in used_seq_ids:
            used_seq_ids.add(candidate)
            return candidate


def main():
    parser = argparse.ArgumentParser(description="Convert active cleaned isolate IDs into stable sequencing IDs.")
    parser.add_argument("input_csv", help="CSV file containing cleaned IDs, usually plate_registry.csv")
    parser.add_argument("--column", default="final_id", help="Column containing cleaned IDs (default: final_id)")
    parser.add_argument("-o", "--output", default="sequencing_ids.csv")
    parser.add_argument("--errors", default="sequencing_id_errors.csv")
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output)
    error_path = Path(args.errors)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        cleaned_ids = load_active_ids(input_path, args.column)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    existing_map, used_seq_ids, max_counters = load_existing_assignments(output_path)
    output_rows = []
    error_rows = []

    for row_no, current_id in enumerate(cleaned_ids, start=2):
        try:
            parsed = parse_current_id(current_id)
        except ValueError as e:
            error_rows.append({"row_number": row_no, "current_id": current_id, "error": str(e)})
            continue

        if current_id in existing_map:
            seq_id = existing_map[current_id]
        else:
            seq_id = next_seq_id(parsed["cultivar_code"], parsed["field"], max_counters, used_seq_ids)

        output_rows.append({
            "seq_id": seq_id,
            "current_id": current_id,
            "cultivar_code": parsed["cultivar_code"],
            "cultivar": parsed["cultivar"],
            "field": parsed["field"],
            "ignored_no": parsed["ignored_no"],
            "type": parsed["type"],
            "layer": parsed["layer"],
            "media": parsed["media"],
            "replicate": parsed["replicate"],
            "isolate_no": parsed["isolate_no"],
        })

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(output_rows)

    if error_rows:
        with error_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["row_number", "current_id", "error"])
            writer.writeheader()
            writer.writerows(error_rows)

    print(f"Done. Wrote {len(output_rows)} active sequencing IDs to {output_path}")
    if error_rows:
        print(f"{len(error_rows)} rows had errors. See {error_path}")
    else:
        print("No errors found.")


if __name__ == "__main__":
    main()
