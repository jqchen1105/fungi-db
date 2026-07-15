#!/usr/bin/env python3

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_FILE = Path("fungi.db")
LOCATIONS_CSV = Path("isolate_locations.csv")

FIELDS = [
    "seq_id",
    "plate_id",
    "category",
    "bag_code",
    "species_group",
    "container",
    "position",
    "notes",
    "updated_at",
]

CATEGORY_CHOICES = {
    "N": "not growing",
    "S": "species bag",
    "T": "to be sequenced",
    "P": "failed PCR",
    "D": "double / duplicate",
    "G": "growing",
    "O": "other",
}


def ensure_locations_csv():
    if not LOCATIONS_CSV.exists():
        with LOCATIONS_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()


def load_locations():
    ensure_locations_csv()
    rows = {}
    with LOCATIONS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            seq_id = (row.get("seq_id") or "").strip().upper()
            if seq_id:
                normalized = {field: row.get(field, "") for field in FIELDS}
                normalized["seq_id"] = seq_id
                rows[seq_id] = normalized
    return rows


def save_locations(rows):
    with LOCATIONS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for seq_id in sorted(rows):
            writer.writerow(rows[seq_id])


def connect_db():
    if not DB_FILE.exists():
        print(f"Error: {DB_FILE} was not found. Run rebuild_database.py first.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def find_isolate(identifier):
    identifier = identifier.strip()
    conn = connect_db()
    try:
        row = conn.execute(
            """
            SELECT seq_id, final_id, cultivar, species, culture_status
            FROM isolates
            WHERE upper(seq_id) = upper(?)
               OR upper(final_id) = upper(?)
               OR upper(original_id) = upper(?)
            LIMIT 1
            """,
            (identifier, identifier, identifier),
        ).fetchone()
        return row
    finally:
        conn.close()


def choose_category(default=""):
    print("\nCategories:")
    for key, label in CATEGORY_CHOICES.items():
        print(f"  {key} = {label}")
    while True:
        value = input(f"Category [{default or 'choose'}]: ").strip().upper() or default
        if value in CATEGORY_CHOICES:
            return value
        print("Choose one of: " + ", ".join(CATEGORY_CHOICES))


def suggested_species_group(species):
    if not species:
        return ""
    parts = species.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def suggested_bag(category, species_group=""):
    if category == "S":
        slug = species_group.replace(" ", "-") if species_group else "Unknown"
        return f"S-{slug}"
    return f"01{category}"


def assign(identifier):
    isolate = find_isolate(identifier)
    if isolate is None:
        print(f"No isolate found for: {identifier}", file=sys.stderr)
        return 1

    rows = load_locations()
    seq_id = isolate["seq_id"]
    current = rows.get(seq_id, {field: "" for field in FIELDS})

    print(f"\nIsolate: {seq_id}")
    print(f"Plate ID: {isolate['final_id'] or ''}")
    print(f"Cultivar: {isolate['cultivar'] or ''}")
    print(f"Species: {isolate['species'] or ''}")
    if current.get("bag_code"):
        print(f"Current bag: {current['bag_code']}")

    category = choose_category(current.get("category", ""))
    species_group = current.get("species_group", "")

    if category == "S":
        default_species = species_group or suggested_species_group(isolate["species"])
        species_group = input(f"Species group [{default_species}]: ").strip() or default_species
    else:
        species_group = ""

    default_bag = current.get("bag_code") or suggested_bag(category, species_group)
    bag_code = input(f"Bag code [{default_bag}]: ").strip() or default_bag
    container = input(f"Container/freezer/box [{current.get('container', '')}]: ").strip() or current.get("container", "")
    position = input(f"Position [{current.get('position', '')}]: ").strip() or current.get("position", "")
    notes = input(f"Notes [{current.get('notes', '')}]: ").strip() or current.get("notes", "")

    rows[seq_id] = {
        "seq_id": seq_id,
        "plate_id": isolate["final_id"] or "",
        "category": category,
        "bag_code": bag_code,
        "species_group": species_group,
        "container": container,
        "position": position,
        "notes": notes,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_locations(rows)
    print(f"\nSaved: {seq_id} -> {bag_code}")
    print("Run `python rebuild_database.py` to update the website.")
    return 0


def show(identifier):
    isolate = find_isolate(identifier)
    if isolate is None:
        print(f"No isolate found for: {identifier}", file=sys.stderr)
        return 1
    row = load_locations().get(isolate["seq_id"])
    print(f"Seq ID: {isolate['seq_id']}")
    print(f"Plate ID: {isolate['final_id'] or ''}")
    print(f"Species: {isolate['species'] or ''}")
    if not row:
        print("Location: not assigned")
        return 0
    for field in ["category", "bag_code", "species_group", "container", "position", "notes", "updated_at"]:
        print(f"{field.replace('_', ' ').title()}: {row.get(field, '')}")
    return 0


def list_bags():
    rows = load_locations().values()
    summary = {}
    for row in rows:
        bag = row.get("bag_code") or "(unassigned)"
        summary[bag] = summary.get(bag, 0) + 1
    if not summary:
        print("No locations recorded.")
        return
    print("Bag\tCount")
    for bag in sorted(summary):
        print(f"{bag}\t{summary[bag]}")


def list_unassigned():
    conn = connect_db()
    rows = load_locations()
    try:
        isolates = conn.execute(
            "SELECT seq_id, final_id, species FROM isolates ORDER BY seq_id"
        ).fetchall()
    finally:
        conn.close()
    print("Seq ID\tPlate ID\tSpecies")
    for isolate in isolates:
        if isolate["seq_id"] not in rows:
            print(f"{isolate['seq_id']}\t{isolate['final_id'] or ''}\t{isolate['species'] or ''}")


def interactive():
    print("Plate Location Manager")
    print("Enter a sequencing ID or plate ID. Type :quit to exit.")
    while True:
        value = input("\nIsolate ID> ").strip()
        if value.lower() in {":quit", ":exit", "q"}:
            break
        if value:
            assign(value)


def main():
    parser = argparse.ArgumentParser(
        description="Assign physical bag/storage locations to isolates already present in fungi.db."
    )
    sub = parser.add_subparsers(dest="command")

    assign_parser = sub.add_parser("assign", help="Assign or change an isolate location")
    assign_parser.add_argument("identifier", help="Sequencing ID, plate ID, or original ID")

    show_parser = sub.add_parser("show", help="Show an isolate location")
    show_parser.add_argument("identifier")

    sub.add_parser("bags", help="List all bags and isolate counts")
    sub.add_parser("unassigned", help="List isolates without a recorded location")
    sub.add_parser("interactive", help="Process many isolates interactively")

    args = parser.parse_args()
    ensure_locations_csv()

    if args.command == "assign":
        raise SystemExit(assign(args.identifier))
    if args.command == "show":
        raise SystemExit(show(args.identifier))
    if args.command == "bags":
        list_bags()
        return
    if args.command == "unassigned":
        list_unassigned()
        return

    interactive()


if __name__ == "__main__":
    main()
