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


def parse_current_id(current_id: str) -> dict:
    s = current_id.strip().upper()
    m = ID_PATTERN.fullmatch(s)
    if not m:
        raise ValueError(
            f"Could not parse cleaned ID '{current_id}'. "
            "Expected format like SPU11P1P1_1"
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

    sample_type = "peel" if sample_type_code == "P" else "crushed"
    media = "pda" if media_code == "P" else "1/10 pda"

    return {
        "cultivar_code": cultivar_code,
        "cultivar": CULTIVAR_NAME[cultivar_code],
        "field": field,
        "ignored_no": ignored_no,
        "type": sample_type,
        "layer": layer,
        "media": media,
        "replicate": replicate,
        "isolate_no": isolate_no,
    }


def load_ids(input_path: Path, column_name: str) -> list[str]:
    with input_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or column_name not in reader.fieldnames:
            raise ValueError(f"Input CSV must contain a column named '{column_name}'")
        return [row[column_name].strip() for row in reader if row.get(column_name, "").strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Convert cleaned isolate IDs into sequencing IDs."
    )
    parser.add_argument("input_csv", help="CSV file containing cleaned IDs")
    parser.add_argument(
        "--column",
        default="current_id",
        help="Column containing cleaned IDs (default: current_id)"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="sequencing_ids.csv",
        help="Output CSV file (default: sequencing_ids.csv)"
    )
    parser.add_argument(
        "--errors",
        default="sequencing_id_errors.csv",
        help="CSV file for parsing errors (default: sequencing_id_errors.csv)"
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_path = Path(args.output)
    error_path = Path(args.errors)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        cleaned_ids = load_ids(input_path, args.column)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not cleaned_ids:
        print("Error: no IDs found in input file.", file=sys.stderr)
        sys.exit(1)

    counters = defaultdict(int)
    seen_ids = set()
    output_rows = []
    error_rows = []

    for row_no, current_id in enumerate(cleaned_ids, start=2):
        if current_id.upper() in seen_ids:
            error_rows.append({
                "row_number": row_no,
                "current_id": current_id,
                "error": "Duplicate cleaned ID in input file"
            })
            continue

        seen_ids.add(current_id.upper())

        try:
            parsed = parse_current_id(current_id)
        except ValueError as e:
            error_rows.append({
                "row_number": row_no,
                "current_id": current_id,
                "error": str(e)
            })
            continue

        cultivar_code = parsed["cultivar_code"]
        field = parsed["field"]

        counter_key = (cultivar_code, field)
        counters[counter_key] += 1

        seq_id = f"{CULTIVAR_PREFIX[cultivar_code]}{field}{counters[counter_key]:03d}"

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
        writer = csv.DictWriter(
            f,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    if error_rows:
        with error_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["row_number", "current_id", "error"]
            )
            writer.writeheader()
            writer.writerows(error_rows)

    print(f"Done. Wrote {len(output_rows)} sequencing IDs to {output_path}")
    if error_rows:
        print(f"{len(error_rows)} rows had errors. See {error_path}")
    else:
        print("No errors found.")


if __name__ == "__main__":
    main()
