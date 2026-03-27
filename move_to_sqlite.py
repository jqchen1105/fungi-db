#!/usr/bin/env python3

import csv
import sqlite3
from pathlib import Path

DB_FILE = "fungi.db"
PLATE_REGISTRY_CSV = "plate_registry.csv"
SEQUENCING_IDS_CSV = "sequencing_ids.csv"


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


def create_tables(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS plate_registry (
        entry_no INTEGER,
        original_id TEXT,
        base_id TEXT,
        original_suffix TEXT,
        original_replate_no TEXT,
        parent_id TEXT,
        final_id TEXT PRIMARY KEY,
        assigned_isolate_no INTEGER,
        changed TEXT,
        reason TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sequencing_ids (
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
    CREATE TABLE IF NOT EXISTS isolates (
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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_plate_registry_base_id ON plate_registry(base_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_plate_registry_original_id ON plate_registry(original_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_seq_current_id ON sequencing_ids(current_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_seq_cultivar ON sequencing_ids(cultivar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_seq_field ON sequencing_ids(field)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_isolates_cultivar ON isolates(cultivar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_isolates_species ON isolates(species)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_isolates_field ON isolates(field)")


def import_plate_registry(conn, rows):
    cur = conn.cursor()
    cur.execute("DELETE FROM plate_registry")

    for row in rows:
        cur.execute("""
        INSERT INTO plate_registry (
            entry_no,
            original_id,
            base_id,
            original_suffix,
            original_replate_no,
            parent_id,
            final_id,
            assigned_isolate_no,
            changed,
            reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            normalize(row.get("reason")),
        ))


def import_sequencing_ids(conn, rows):
    cur = conn.cursor()
    cur.execute("DELETE FROM sequencing_ids")

    for row in rows:
        cur.execute("""
        INSERT INTO sequencing_ids (
            seq_id,
            current_id,
            cultivar_code,
            cultivar,
            field,
            ignored_no,
            type,
            layer,
            media,
            replicate,
            isolate_no
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


def build_isolates_table(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM isolates")

    cur.execute("""
    INSERT INTO isolates (
        seq_id,
        final_id,
        original_id,
        base_id,
        parent_id,
        cultivar_code,
        cultivar,
        field,
        ignored_no,
        type,
        layer,
        media,
        replicate,
        isolate_no,
        assigned_isolate_no,
        changed,
        reason
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
        p.reason
    FROM sequencing_ids s
    LEFT JOIN plate_registry p
        ON s.current_id = p.final_id
    """)


def main():
    plate_rows = read_csv(PLATE_REGISTRY_CSV)
    seq_rows = read_csv(SEQUENCING_IDS_CSV)

    conn = sqlite3.connect(DB_FILE)
    try:
        create_tables(conn)
        import_plate_registry(conn, plate_rows)
        import_sequencing_ids(conn, seq_rows)
        build_isolates_table(conn)
        conn.commit()

        cur = conn.cursor()
        plate_count = cur.execute("SELECT COUNT(*) FROM plate_registry").fetchone()[0]
        seq_count = cur.execute("SELECT COUNT(*) FROM sequencing_ids").fetchone()[0]
        isolate_count = cur.execute("SELECT COUNT(*) FROM isolates").fetchone()[0]

        print(f"Done. Created/updated {DB_FILE}")
        print(f"plate_registry rows: {plate_count}")
        print(f"sequencing_ids rows: {seq_count}")
        print(f"isolates rows: {isolate_count}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
