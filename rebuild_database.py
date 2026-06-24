#!/usr/bin/env python3

import csv
import sqlite3
from pathlib import Path

DB_FILE = "fungi.db"
PLATE_REGISTRY_CSV = "plate_registry.csv"
SEQUENCING_IDS_CSV = "sequencing_ids.csv"
ANNOTATIONS_CSV = "isolate_annotations.csv"

ANNOTATION_FIELDS = [
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


def normalize(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value != "" else None


def read_csv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def ensure_annotations_csv(path=ANNOTATIONS_CSV):
    path = Path(path)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ANNOTATION_FIELDS)
            writer.writeheader()
        print(f"Created empty {path}")


def create_tables(conn):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS isolates")
    cur.execute("DROP TABLE IF EXISTS sequencing_ids")
    cur.execute("DROP TABLE IF EXISTS plate_registry")
    cur.execute("DROP TABLE IF EXISTS isolate_annotations")

    cur.execute("""
    CREATE TABLE plate_registry (
        entry_no INTEGER,
        original_id TEXT,
        base_id TEXT,
        original_suffix TEXT,
        original_replate_no TEXT,
        parent_id TEXT,
        final_id TEXT PRIMARY KEY,
        assigned_isolate_no INTEGER,
        changed TEXT,
        status TEXT DEFAULT 'active',
        reason TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE sequencing_ids (
        seq_id TEXT PRIMARY KEY,
        current_id TEXT UNIQUE,
        cultivar_code TEXT,
        cultivar TEXT,
        field TEXT,
        ignored_no TEXT,
        type TEXT,
        layer TEXT,
        media TEXT,
        replicate TEXT,
        isolate_no TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE isolate_annotations (
        seq_id TEXT PRIMARY KEY,
        species TEXT,
        blast_top_hit TEXT,
        blast_accession TEXT,
        blast_identity REAL,
        blast_query_coverage REAL,
        blast_evalue TEXT,
        fasta_path TEXT,
        fasta_sequence TEXT,
        image_path TEXT,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE isolates (
        seq_id TEXT PRIMARY KEY,
        final_id TEXT UNIQUE,
        original_id TEXT,
        base_id TEXT,
        parent_id TEXT,
        cultivar_code TEXT,
        cultivar TEXT,
        field TEXT,
        ignored_no TEXT,
        type TEXT,
        layer TEXT,
        media TEXT,
        replicate TEXT,
        isolate_no TEXT,
        assigned_isolate_no INTEGER,
        changed TEXT,
        status TEXT,
        reason TEXT,
        species TEXT,
        blast_top_hit TEXT,
        blast_accession TEXT,
        blast_identity REAL,
        blast_query_coverage REAL,
        blast_evalue TEXT,
        fasta_path TEXT,
        fasta_sequence TEXT,
        image_path TEXT,
        notes TEXT,
        FOREIGN KEY(final_id) REFERENCES plate_registry(final_id),
        FOREIGN KEY(seq_id) REFERENCES sequencing_ids(seq_id)
    )
    """)

    cur.execute("CREATE INDEX idx_plate_registry_base_id ON plate_registry(base_id)")
    cur.execute("CREATE INDEX idx_plate_registry_status ON plate_registry(status)")
    cur.execute("CREATE INDEX idx_seq_current_id ON sequencing_ids(current_id)")
    cur.execute("CREATE INDEX idx_seq_cultivar ON sequencing_ids(cultivar)")
    cur.execute("CREATE INDEX idx_isolates_cultivar ON isolates(cultivar)")
    cur.execute("CREATE INDEX idx_isolates_species ON isolates(species)")
    cur.execute("CREATE INDEX idx_isolates_status ON isolates(status)")


def import_plate_registry(conn, rows):
    cur = conn.cursor()
    for row in rows:
        cur.execute("""
        INSERT INTO plate_registry (
            entry_no, original_id, base_id, original_suffix, original_replate_no,
            parent_id, final_id, assigned_isolate_no, changed, status, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            normalize(row.get("entry_no")),
            normalize(row.get("original_id")),
            normalize(row.get("base_id")),
            normalize(row.get("original_suffix")),
            normalize(row.get("original_replate_no")),
            normalize(row.get("parent_id")),
            normalize(row.get("final_id")),
            normalize(row.get("assigned_isolate_no")),
            normalize(row.get("changed")),
            normalize(row.get("status") or "active"),
            normalize(row.get("reason")),
        ))


def import_sequencing_ids(conn, rows):
    cur = conn.cursor()
    for row in rows:
        cur.execute("""
        INSERT INTO sequencing_ids (
            seq_id, current_id, cultivar_code, cultivar, field, ignored_no,
            type, layer, media, replicate, isolate_no
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            normalize(row.get("seq_id")),
            normalize(row.get("current_id")),
            normalize(row.get("cultivar_code")),
            normalize(row.get("cultivar")),
            normalize(row.get("field")),
            normalize(row.get("ignored_no")),
            normalize(row.get("type")),
            normalize(row.get("layer")),
            normalize(row.get("media")),
            normalize(row.get("replicate")),
            normalize(row.get("isolate_no")),
        ))


def import_annotations(conn, rows):
    cur = conn.cursor()
    for row in rows:
        seq_id = normalize(row.get("seq_id"))
        if not seq_id:
            continue
        cur.execute("""
        INSERT INTO isolate_annotations (
            seq_id, species, blast_top_hit, blast_accession, blast_identity,
            blast_query_coverage, blast_evalue, fasta_path, fasta_sequence,
            image_path, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            seq_id,
            normalize(row.get("species")),
            normalize(row.get("blast_top_hit")),
            normalize(row.get("blast_accession")),
            normalize(row.get("blast_identity")),
            normalize(row.get("blast_query_coverage")),
            normalize(row.get("blast_evalue")),
            normalize(row.get("fasta_path")),
            normalize(row.get("fasta_sequence")),
            normalize(row.get("image_path")),
            normalize(row.get("notes")),
        ))


def build_isolates_table(conn):
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO isolates (
        seq_id, final_id, original_id, base_id, parent_id,
        cultivar_code, cultivar, field, ignored_no, type, layer, media,
        replicate, isolate_no, assigned_isolate_no, changed, status, reason,
        species, blast_top_hit, blast_accession, blast_identity,
        blast_query_coverage, blast_evalue, fasta_path, fasta_sequence,
        image_path, notes
    )
    SELECT
        s.seq_id,
        p.final_id,
        p.original_id,
        p.base_id,
        p.parent_id,
        s.cultivar_code,
        s.cultivar,
        s.field,
        s.ignored_no,
        s.type,
        s.layer,
        s.media,
        s.replicate,
        s.isolate_no,
        p.assigned_isolate_no,
        p.changed,
        COALESCE(p.status, 'active') AS status,
        p.reason,
        a.species,
        a.blast_top_hit,
        a.blast_accession,
        a.blast_identity,
        a.blast_query_coverage,
        a.blast_evalue,
        a.fasta_path,
        a.fasta_sequence,
        a.image_path,
        a.notes
    FROM sequencing_ids s
    LEFT JOIN plate_registry p ON s.current_id = p.final_id
    LEFT JOIN isolate_annotations a ON s.seq_id = a.seq_id
    WHERE COALESCE(p.status, 'active') = 'active'
    """)


def main():
    ensure_annotations_csv()

    plate_rows = read_csv(PLATE_REGISTRY_CSV)
    seq_rows = read_csv(SEQUENCING_IDS_CSV)
    annotation_rows = read_csv(ANNOTATIONS_CSV)

    conn = sqlite3.connect(DB_FILE)
    try:
        create_tables(conn)
        import_plate_registry(conn, plate_rows)
        import_sequencing_ids(conn, seq_rows)
        import_annotations(conn, annotation_rows)
        build_isolates_table(conn)
        conn.commit()

        cur = conn.cursor()
        plate_count = cur.execute("SELECT COUNT(*) FROM plate_registry").fetchone()[0]
        removed_count = cur.execute("SELECT COUNT(*) FROM plate_registry WHERE status = 'removed'").fetchone()[0]
        seq_count = cur.execute("SELECT COUNT(*) FROM sequencing_ids").fetchone()[0]
        annotation_count = cur.execute("SELECT COUNT(*) FROM isolate_annotations").fetchone()[0]
        isolate_count = cur.execute("SELECT COUNT(*) FROM isolates").fetchone()[0]

        print(f"Done. Rebuilt {DB_FILE}")
        print(f"plate_registry rows: {plate_count} ({removed_count} removed)")
        print(f"sequencing_ids rows: {seq_count}")
        print(f"annotation rows: {annotation_count}")
        print(f"active website isolates: {isolate_count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
