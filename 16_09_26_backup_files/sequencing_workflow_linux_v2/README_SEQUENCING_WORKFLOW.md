# Sequencing Workflow Manager

This is a fast interactive Linux tool for tracking how fungal isolates move through DNA extraction, PCR and sequencing.

It uses the existing `fungi.db` to look up isolates, so you do not need to type the metadata again.

It stores the workflow in:

```text
sequencing_workflow.csv
```

Keep this CSV. It is the master record for this workflow.

## Install

Put these files in:

```bash
~/fungi-db-updated
```

Files:

```text
sequencing_workflow_manager.py
sequencing_workflow.csv
```

Run:

```bash
cd ~/fungi-db-updated
python sequencing_workflow_manager.py
```

## Basic use

Type an isolate ID:

```text
workflow> E1021
```

You can also use the plate ID:

```text
workflow> SPU11P2Q2_1
```

The program shows the isolate and asks what you want to update.

## Reference isolates

Set the isolate that you actually sequence to:

```text
reference
```

The program then shows ONLY the other isolates from the same `base_id`.

Example:

```text
SPU11P2Q2_1 = reference

SPU11P2Q2_2 = cross-reference -> E1021
SPU11P2Q2_3 = cross-reference -> E1021
SPU11P2Q2_4 = cross-reference -> E1021
```

This prevents accidentally linking isolates from different source plates.

## Status fields

DNA:

```text
not extracted
extracted
low concentration
poor quality
```

PCR:

```text
not attempted
successful
failed
double band
weak band
```

Sequencing:

```text
not sent
not required
sent
successful
messy
failed
```

Role:

```text
undecided
direct
reference
cross-reference
morphology ID
```

## Fast commands

These are useful while working at the bench:

```text
E1021 pcr-ok
E1022 pcr-fail
E1023 pcr-double
E1024 dna-low
E1025 seq-sent
E1026 seq-ok
E1027 seq-messy
E1028 seq-fail
```

## Overview commands

Inside the program:

```text
:all
:problems
:refs
:unprocessed
:help
:quit
```

For example:

```text
workflow> :problems
```

shows low-concentration DNA, failed/double/weak PCRs and messy/failed sequencing.

```text
workflow> :refs
```

shows all reference groups.

## Git backup

Remember to push this file:

```bash
git add sequencing_workflow.csv sequencing_workflow_manager.py
git commit -m "Update sequencing workflow"
git push
```

Later, `sequencing_workflow.csv` can also be imported into the Flask website so you can see Role, Reference, PCR status and Sequencing status in the online table.


## Morphology-only identifications

Use `morphology ID` when you deliberately do not sequence an isolate because the species is obvious from morphology and there is no specific sequenced reference isolate for it.

Example:

```text
SPU11P2Q3_1
Role: morphology ID
Reference: -
Sequencing: not required
```

When you choose `morphology ID`, the manager automatically changes sequencing status from `not sent` to `not required`.
