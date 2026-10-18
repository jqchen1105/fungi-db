
#!/usr/bin/env python3

import csv
import sqlite3
from pathlib import Path

DB_FILE = Path("fungi.db")
CSV_FILE = Path("isolate_annotations.csv")
STATUS = "inactive after first plating"

pending = []


def find_isolate(seq_id):
    """Check that the sequencing ID actually exists."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT seq_id, final_id, species, culture_status
        FROM isolates
        WHERE upper(seq_id) = upper(?)
    """, (seq_id,)).fetchone()

    conn.close()
    return row


def show_list():
    if not pending:
        print("\nNo isolates currently in the list.\n")
        return

    print("\nIsolates to mark inactive:")
    for i, seq_id in enumerate(pending, start=1):
        isolate = find_isolate(seq_id)
        plate = isolate["final_id"] if isolate else ""
        print(f"  {i}) {seq_id}  {plate or ''}")
    print()


def delete_isolate():
    if not pending:
        print("\nNothing to delete.\n")
        return

    show_list()

    value = input("Number or isolate ID to delete: ").strip()

    if value.isdigit():
        number = int(value)

        if 1 <= number <= len(pending):
            removed = pending.pop(number - 1)
            print(f"\nRemoved {removed}\n")
        else:
            print("\nInvalid number.\n")
        return

    seq_id = value.upper()

    if seq_id in pending:
        pending.remove(seq_id)
        print(f"\nRemoved {seq_id}\n")
    else:
        print(f"\n{seq_id} is not in the list.\n")


def save_changes():
    if not pending:
        print("\nNothing to save.\n")
        return

    # Read existing annotation file
    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    # Make sure culture_status exists
    if "culture_status" not in fields:
        print("\nERROR: culture_status column is missing.")
        return

    existing = {}

    for row in rows:
        seq_id = (row.get("seq_id") or "").strip().upper()
        if seq_id:
            existing[seq_id] = row

    updated = []
    created = []

    for seq_id in pending:

        if seq_id in existing:
            existing[seq_id]["culture_status"] = STATUS
            updated.append(seq_id)

        else:
            # Create a brand-new annotation row
            new_row = {field: "" for field in fields}
            new_row["seq_id"] = seq_id
            new_row["culture_status"] = STATUS

            rows.append(new_row)
            existing[seq_id] = new_row
            created.append(seq_id)

    # Write everything back
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print("\nSaved successfully!")

    if updated:
        print("\nExisting annotation rows updated:")
        for seq_id in updated:
            print(f"  ✓ {seq_id}")

    if created:
        print("\nNew annotation rows created:")
        for seq_id in created:
            print(f"  ✓ {seq_id}")

    print(f"\nStatus: {STATUS}")
    print(f"Total: {len(pending)} isolate(s)")

    pending.clear()

    print("\nNow run:")
    print("  python rebuild_database.py")
    print()


print("""
=====================================
     INACTIVE ISOLATE MANAGER
=====================================

Status: inactive after first plating

Type a sequencing ID to add it.

Commands:
  :list     Show current list
  :delete   Delete an isolate from list
  :save     Save changes
  :quit     Exit
""")

while True:

    value = input("inactive> ").strip()

    if not value:
        continue

    if value == ":list":
        show_list()

    elif value == ":delete":
        delete_isolate()

    elif value == ":save":
        save_changes()

    elif value == ":quit":

        if pending:
            print("\nYou have unsaved isolates:")
            show_list()

            answer = input("Quit without saving? (y/n): ").strip().lower()

            if answer != "y":
                continue

        print("Bye!")
        break

    elif value.startswith(":"):
        print("\nUnknown command. Use :list, :delete, :save or :quit.\n")

    else:
        seq_id = value.upper()

        isolate = find_isolate(seq_id)

        if not isolate:
            print(f"  ✗ {seq_id} not found in fungi.db")
            continue

        if seq_id in pending:
            print(f"  {seq_id} is already in the list.")
            continue

        pending.append(seq_id)

        plate = isolate["final_id"] or ""
        current = isolate["culture_status"] or "not tested"

        print(f"  + {seq_id} | {plate} | currently: {current}")
