#!/usr/bin/env python3

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_FILE = Path("fungi.db")
WORKFLOW_FILE = Path("sequencing_workflow.csv")
ANNOTATIONS_FILE = Path("isolate_annotations.csv")

FIELDS = [
    "seq_id",
    "plate_id",
    "base_id",
    "role",
    "reference_seq_id",
    "dna_status",
    "pcr_status",
    "sequencing_status",
    "notes",
    "updated_at",
]

ROLE_OPTIONS = [
    "undecided",
    "direct",
    "reference",
    "cross-reference",
    "morphology ID",
]

DNA_OPTIONS = [
    "not extracted",
    "extracted",
    "low concentration",
    "poor quality",
]

PCR_OPTIONS = [
    "not attempted",
    "successful",
    "failed",
    "double band",
    "weak band",
]

SEQ_OPTIONS = [
    "not sent",
    "not required",
    "sent",
    "successful",
    "messy",
    "failed",
]


def ensure_workflow_file():
    if not WORKFLOW_FILE.exists():
        with WORKFLOW_FILE.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writeheader()


def load_workflow():
    ensure_workflow_file()
    rows = {}
    with WORKFLOW_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            seq_id = (row.get("seq_id") or "").strip()
            if seq_id:
                clean = {field: row.get(field, "") for field in FIELDS}
                rows[seq_id] = clean
    return rows


def save_workflow(rows):
    with WORKFLOW_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for seq_id in sorted(rows):
            writer.writerow(rows[seq_id])


def connect_db():
    if not DB_FILE.exists():
        print("ERROR: fungi.db not found in this folder.")
        print("Run this script from ~/fungi-db-updated")
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
            SELECT
                seq_id,
                final_id,
                original_id,
                base_id,
                species,
                cultivar,
                culture_status
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


def same_base_plate(base_id):
    conn = connect_db()
    try:
        rows = conn.execute(
            """
            SELECT seq_id, final_id, base_id, species, isolate_no
            FROM isolates
            WHERE base_id = ?
            ORDER BY
                CASE
                    WHEN isolate_no GLOB '[0-9]*' THEN CAST(isolate_no AS INTEGER)
                    ELSE 999999
                END,
                seq_id
            """,
            (base_id,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def default_row(isolate):
    return {
        "seq_id": isolate["seq_id"],
        "plate_id": isolate["final_id"] or "",
        "base_id": isolate["base_id"] or "",
        "role": "undecided",
        "reference_seq_id": "",
        "dna_status": "not extracted",
        "pcr_status": "not attempted",
        "sequencing_status": "not sent",
        "notes": "",
        "updated_at": "",
    }



def get_species_options():
    conn = connect_db()
    try:
        rows = conn.execute("""
            SELECT DISTINCT species FROM isolates
            WHERE species IS NOT NULL AND TRIM(species) != ''
            ORDER BY species COLLATE NOCASE
        """).fetchall()
        return [row["species"] for row in rows]
    finally:
        conn.close()


def update_species_annotation(seq_id, species):
    if not ANNOTATIONS_FILE.exists():
        print(f"\\nERROR: {ANNOTATIONS_FILE} not found.")
        return False
    with ANNOTATIONS_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    if "seq_id" not in fields or "species" not in fields:
        print("\\nERROR: isolate_annotations.csv is missing seq_id or species column.")
        return False
    found = False
    for row in rows:
        if (row.get("seq_id") or "").strip().upper() == seq_id.upper():
            row["species"] = species
            found = True
            break
    if not found:
        new_row = {field: "" for field in fields}
        new_row["seq_id"] = seq_id
        new_row["species"] = species
        rows.append(new_row)
    with ANNOTATIONS_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return True


def choose_morphology_species(isolate):
    options = get_species_options()
    current = isolate["species"] or ""
    print("\\nMorphological identification")
    print(f"Current species: {current or '-'}")
    print("\\nSpecies already present in your database:")
    for i, species in enumerate(options, 1):
        star = "*" if species == current else " "
        print(f" {star} {i}) {species}")
    manual = len(options) + 1
    print(f"   {manual}) Enter species manually")
    print(" 0) Cancel")
    while True:
        answer = input("Species choice: ").strip()
        if answer in {"", "0"}:
            return None
        if answer.isdigit():
            n = int(answer)
            if 1 <= n <= len(options):
                return options[n - 1]
            if n == manual:
                species = input("Species name: ").strip()
                if species:
                    return species
        print("Invalid choice.")

def choose(label, options, current):
    print(f"\n{label}")
    for i, option in enumerate(options, 1):
        marker = "*" if option == current else " "
        print(f" {marker} {i}) {option}")

    while True:
        answer = input(f"Choose 1-{len(options)} [Enter = keep]: ").strip()

        if answer == "":
            return current

        if answer.isdigit():
            number = int(answer)
            if 1 <= number <= len(options):
                return options[number - 1]

        print("Invalid choice.")


def print_record(isolate, row):
    print("\n" + "=" * 72)
    print(f"Seq ID:       {isolate['seq_id']}")
    print(f"Plate ID:     {isolate['final_id'] or ''}")
    print(f"Base plate:   {isolate['base_id'] or ''}")
    print(f"Species:      {isolate['species'] or ''}")
    print(f"Culture:      {isolate['culture_status'] or ''}")
    print("-" * 72)
    print(f"Role:         {row.get('role') or 'undecided'}")
    print(f"Reference:    {row.get('reference_seq_id') or '-'}")
    print(f"DNA:          {row.get('dna_status') or 'not extracted'}")
    print(f"PCR:          {row.get('pcr_status') or 'not attempted'}")
    print(f"Sequencing:   {row.get('sequencing_status') or 'not sent'}")
    print(f"Notes:        {row.get('notes') or '-'}")
    print("=" * 72)


def choose_reference(isolate, workflow):
    candidates = [
        r for r in same_base_plate(isolate["base_id"])
        if r["seq_id"] != isolate["seq_id"]
    ]

    if not candidates:
        print("\nNo other isolates from the same base plate.")
        return ""

    print("\nPossible references from SAME base plate:")
    for i, candidate in enumerate(candidates, 1):
        wf = workflow.get(candidate["seq_id"], {})
        extra = []
        if candidate["species"]:
            extra.append(candidate["species"])
        if wf.get("role"):
            extra.append(f"role={wf['role']}")
        extra_text = " | " + " | ".join(extra) if extra else ""
        print(f" {i}) {candidate['seq_id']} | {candidate['final_id']}{extra_text}")

    while True:
        answer = input("Reference number [Enter = cancel]: ").strip()

        if answer == "":
            return ""

        if answer.isdigit():
            number = int(answer)
            if 1 <= number <= len(candidates):
                return candidates[number - 1]["seq_id"]

        print("Invalid choice.")


def assign_children_to_reference(reference_isolate, workflow):
    candidates = [
        r for r in same_base_plate(reference_isolate["base_id"])
        if r["seq_id"] != reference_isolate["seq_id"]
    ]

    if not candidates:
        return

    print("\nOther isolates from the same base plate:")
    for i, candidate in enumerate(candidates, 1):
        wf = workflow.get(candidate["seq_id"], {})
        current_ref = wf.get("reference_seq_id", "")
        suffix = f" | current ref={current_ref}" if current_ref else ""
        print(f" {i}) {candidate['seq_id']} | {candidate['final_id']}{suffix}")

    print("\nEnter the numbers that this isolate represents.")
    print("Example: 1,2,4")
    answer = input("Cross-reference isolates [Enter = none]: ").strip()

    if not answer:
        return

    try:
        selected = sorted({int(x.strip()) for x in answer.split(",")})
    except ValueError:
        print("Invalid list. Nothing changed.")
        return

    if any(n < 1 or n > len(candidates) for n in selected):
        print("Invalid list. Nothing changed.")
        return

    for n in selected:
        candidate = candidates[n - 1]
        child = workflow.get(candidate["seq_id"], default_row(candidate))
        child["role"] = "cross-reference"
        child["reference_seq_id"] = reference_isolate["seq_id"]
        child["plate_id"] = candidate["final_id"] or ""
        child["base_id"] = candidate["base_id"] or ""
        child["updated_at"] = datetime.now().isoformat(timespec="seconds")
        workflow[candidate["seq_id"]] = child
        print(f" linked {candidate['seq_id']} -> {reference_isolate['seq_id']}")


def edit_isolate(identifier, workflow):
    isolate = find_isolate(identifier)

    if isolate is None:
        print(f"\nNo isolate found for: {identifier}")
        return

    row = workflow.get(isolate["seq_id"], default_row(isolate))
    print_record(isolate, row)

    print("\nWhat do you want to change?")
    print(" 1) Role / reference")
    print(" 2) DNA status")
    print(" 3) PCR status")
    print(" 4) Sequencing status")
    print(" 5) Notes")
    print(" 6) Edit everything")
    print(" 7) Show only")
    print(" 0) Back")

    action = input("Choice: ").strip()

    if action == "0":
        return

    if action == "7":
        return

    edit_all = action == "6"

    if action == "1" or edit_all:
        role = choose("Sequencing role", ROLE_OPTIONS, row.get("role") or "undecided")
        row["role"] = role

        if role == "cross-reference":
            ref = choose_reference(isolate, workflow)
            if ref:
                row["reference_seq_id"] = ref
        else:
            row["reference_seq_id"] = ""

        if role == "reference":
            assign_children_to_reference(isolate, workflow)

        if role == "morphology ID":
            species = choose_morphology_species(isolate)
            if species and update_species_annotation(isolate["seq_id"], species):
                print(f"\nSpecies saved: {species}")
                print("Saved to isolate_annotations.csv.")
            if row.get("sequencing_status") == "not sent":
                row["sequencing_status"] = "not required"
                print("Sequencing status automatically set to 'not required'.")

    if action == "2" or edit_all:
        row["dna_status"] = choose(
            "DNA status",
            DNA_OPTIONS,
            row.get("dna_status") or "not extracted",
        )

    if action == "3" or edit_all:
        row["pcr_status"] = choose(
            "PCR status",
            PCR_OPTIONS,
            row.get("pcr_status") or "not attempted",
        )

    if action == "4" or edit_all:
        row["sequencing_status"] = choose(
            "Sequencing status",
            SEQ_OPTIONS,
            row.get("sequencing_status") or "not sent",
        )

    if action == "5" or edit_all:
        old_notes = row.get("notes", "")
        answer = input(f"\nNotes [{old_notes or 'none'}] [Enter = keep]: ").strip()
        if answer:
            row["notes"] = answer

    row["plate_id"] = isolate["final_id"] or ""
    row["base_id"] = isolate["base_id"] or ""
    row["updated_at"] = datetime.now().isoformat(timespec="seconds")
    workflow[isolate["seq_id"]] = row
    save_workflow(workflow)

    print("\nSaved.")
    print_record(isolate, row)


def show_all(workflow):
    print("\nSeq ID\tRole\tReference\tDNA\tPCR\tSequencing")
    for seq_id in sorted(workflow):
        row = workflow[seq_id]
        print(
            f"{seq_id}\t"
            f"{row.get('role','')}\t"
            f"{row.get('reference_seq_id','')}\t"
            f"{row.get('dna_status','')}\t"
            f"{row.get('pcr_status','')}\t"
            f"{row.get('sequencing_status','')}"
        )


def show_problems(workflow):
    print("\nProblem samples")
    found = False

    for seq_id in sorted(workflow):
        row = workflow[seq_id]

        problem = (
            row.get("dna_status") in {"low concentration", "poor quality"}
            or row.get("pcr_status") in {"failed", "double band", "weak band"}
            or row.get("sequencing_status") in {"messy", "failed"}
        )

        if problem:
            found = True
            print(
                f"{seq_id}: "
                f"DNA={row.get('dna_status')} | "
                f"PCR={row.get('pcr_status')} | "
                f"Seq={row.get('sequencing_status')}"
            )

    if not found:
        print("None recorded.")


def show_reference_groups(workflow):
    refs = [
        seq_id for seq_id, row in workflow.items()
        if row.get("role") == "reference"
    ]

    print("\nReference groups")

    if not refs:
        print("None recorded.")
        return

    for ref in sorted(refs):
        children = sorted(
            seq_id for seq_id, row in workflow.items()
            if row.get("reference_seq_id") == ref
        )
        print(f"{ref} -> {', '.join(children) if children else '(none linked)'}")


def show_unprocessed(workflow):
    conn = connect_db()
    try:
        isolates = conn.execute(
            "SELECT seq_id, final_id, base_id, species FROM isolates ORDER BY seq_id"
        ).fetchall()
    finally:
        conn.close()

    print("\nIsolates without workflow record")

    count = 0
    for isolate in isolates:
        if isolate["seq_id"] not in workflow:
            count += 1
            print(
                f"{isolate['seq_id']} | "
                f"{isolate['final_id'] or ''} | "
                f"{isolate['species'] or ''}"
            )

    if count == 0:
        print("None.")


def quick_status(identifier, field, value, workflow):
    isolate = find_isolate(identifier)

    if isolate is None:
        print(f"No isolate found for: {identifier}")
        return

    row = workflow.get(isolate["seq_id"], default_row(isolate))
    row[field] = value
    row["plate_id"] = isolate["final_id"] or ""
    row["base_id"] = isolate["base_id"] or ""
    row["updated_at"] = datetime.now().isoformat(timespec="seconds")
    workflow[isolate["seq_id"]] = row
    save_workflow(workflow)
    print(f"Saved {isolate['seq_id']}: {field} = {value}")


def print_help():
    print("""
Commands:
  :all          show all workflow records
  :problems     show failed PCR / double band / low DNA / messy sequencing
  :refs         show reference groups
  :unprocessed  isolates not entered yet
  :help         show commands
  :quit         exit

Quick commands:
  ID pcr-fail
  ID pcr-double
  ID pcr-ok
  ID dna-low
  ID dna-ok
  ID seq-not-required
  ID seq-sent
  ID seq-ok
  ID seq-messy
  ID seq-fail

Examples:
  E1021
  SPU11P2Q2_1
  E1021 pcr-ok
  E1021 seq-sent
""")


QUICK = {
    "pcr-fail": ("pcr_status", "failed"),
    "pcr-double": ("pcr_status", "double band"),
    "pcr-weak": ("pcr_status", "weak band"),
    "pcr-ok": ("pcr_status", "successful"),
    "dna-low": ("dna_status", "low concentration"),
    "dna-poor": ("dna_status", "poor quality"),
    "dna-ok": ("dna_status", "extracted"),
    "seq-not-required": ("sequencing_status", "not required"),
    "seq-sent": ("sequencing_status", "sent"),
    "seq-ok": ("sequencing_status", "successful"),
    "seq-messy": ("sequencing_status", "messy"),
    "seq-fail": ("sequencing_status", "failed"),
}


def interactive():
    workflow = load_workflow()

    print("\nFungi sequencing workflow manager")
    print("Type an isolate ID to work on it.")
    print("Use :help for commands.\n")

    while True:
        value = input("workflow> ").strip()

        if not value:
            continue

        lower = value.lower()

        if lower in {":quit", ":exit", "q"}:
            break

        if lower == ":help":
            print_help()
            continue

        if lower == ":all":
            show_all(workflow)
            continue

        if lower == ":problems":
            show_problems(workflow)
            continue

        if lower == ":refs":
            show_reference_groups(workflow)
            continue

        if lower == ":unprocessed":
            show_unprocessed(workflow)
            continue

        parts = value.split()

        if len(parts) == 2 and parts[1].lower() in QUICK:
            field, status = QUICK[parts[1].lower()]
            quick_status(parts[0], field, status, workflow)
            continue

        edit_isolate(value, workflow)


if __name__ == "__main__":
    ensure_workflow_file()
    interactive()
