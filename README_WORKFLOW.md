# Fungi database workflow

This version keeps the CSV files as the master data. The SQLite database is rebuilt from the CSV files whenever you update something.

## Master files

- `plate_registry.csv` = all isolates and their cleaned/final plate IDs. This includes `status`, so isolates can be marked `active` or `removed`.
- `sequencing_ids.csv` = generated stable sequencing IDs. Do not manually edit unless you really need to fix an ID.
- `isolate_annotations.csv` = species, BLAST, FASTA, image paths, and notes. This is the main file to manually fill after sequencing/identification.
- `fungi.db` = generated database used by the website.

## Add new isolates

```bash
python interactive_plate_organizer.py
```

Then type IDs like:

```text
SPU11P1P1_1
SPU11P1P1_1-4
SPU11P1P1_14 (1)
```

This updates `plate_registry.csv`.

## Mark an isolate as removed

Do not delete the row. Mark it removed so its number is never reused.

```bash
python interactive_plate_organizer.py --remove SPU11P1P1_6
```

Restore it if needed:

```bash
python interactive_plate_organizer.py --restore SPU11P1P1_6
```

## Generate sequencing IDs

```bash
python make_sequencing_ids.py plate_registry.csv --column final_id
```

This creates/updates `sequencing_ids.csv`. Existing sequencing IDs stay stable, even if isolates are removed or new ones are added.

## Add species, BLAST results, notes, FASTA paths, image paths

Edit `isolate_annotations.csv` manually. Match rows by `seq_id`.

Example:

```csv
seq_id,species,blast_top_hit,blast_accession,blast_identity,blast_query_coverage,blast_evalue,fasta_path,fasta_sequence,image_path,notes
A1001,Fusarium oxysporum,Fusarium oxysporum isolate X,AB123456,99.8,98,0.0,data/A1001.fasta,,images/A1001.jpg,looks good
```

## Rebuild the database

```bash
python rebuild_database.py
```

This rebuilds `fungi.db` from the CSV files. Removed isolates are kept in `plate_registry`, but they do not appear on the website.

## Run the website

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

## Full normal workflow

After adding/removing isolates:

```bash
python interactive_plate_organizer.py
python make_sequencing_ids.py plate_registry.csv --column final_id
python rebuild_database.py
python app.py
```

After only changing species/BLAST/notes:

```bash
python rebuild_database.py
python app.py
```
