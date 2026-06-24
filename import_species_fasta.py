#!/usr/bin/env python3

import csv
import sys
from pathlib import Path

ANNOTATION_FILE = "isolate_annotations.csv"

FIELDS = [
    "seq_id",
    "species",
    "blast_top_hit",
    "blast_accession",
    "blast_identity",
    "blast_query_coverage",
    "blast_evalue",
    "fasta_path",
    "fasta_sequence",
    "image_path",
    "notes",
]


def read_fasta(path):
    lines = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            lines.append(line)
    return "".join(lines)


def species_from_folder(folder_name):
    # Example: Colletotrichum_coccodes_115 -> Colletotrichum coccodes
    parts = folder_name.split("_")
    if parts[-1].isdigit():
        parts = parts[:-1]
    return " ".join(parts)


def seq_id_from_filename(filename):
    # Example: B1005_76565_ITS1F_good.fasta -> B1005
    return filename.split("_")[0]


def load_annotations():
    path = Path(ANNOTATION_FILE)
    rows = {}

    if not path.exists():
        return rows

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seq_id = row.get("seq_id", "").strip()
            if seq_id:
                rows[seq_id] = row

    return rows


def save_annotations(rows):
    with open(ANNOTATION_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows.values())


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_species_fasta.py path/to/species_folder")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.exists() or not folder.is_dir():
        print(f"Error: folder not found: {folder}")
        sys.exit(1)

    species = species_from_folder(folder.name)
    rows = load_annotations()

    fasta_files = list(folder.glob("*.fasta")) + list(folder.glob("*.fa")) + list(folder.glob("*.fas"))

    if not fasta_files:
        print("No FASTA files found.")
        sys.exit(1)

    updated = 0

    for fasta in fasta_files:
        seq_id = seq_id_from_filename(fasta.name)
        sequence = read_fasta(fasta)

        row = rows.get(seq_id, {field: "" for field in FIELDS})
        row["seq_id"] = seq_id
        row["species"] = species
        row["blast_top_hit"] = species
        row["fasta_path"] = str(fasta)
        row["fasta_sequence"] = sequence

        note = row.get("notes", "")
        import_note = f"Imported from folder {folder.name}"
        if import_note not in note:
            row["notes"] = (note + "; " + import_note).strip("; ")

        rows[seq_id] = row
        updated += 1

    save_annotations(rows)

    print(f"Updated {updated} isolates in {ANNOTATION_FILE}")
    print(f"Species: {species}")


if __name__ == "__main__":
    main()
