# Physical isolate location update

This update links physical bag/storage locations to the isolates already in `fungi.db`.

## Files

- `plate_location_manager.py`: interactive terminal manager
- `isolate_locations.csv`: master location file
- `rebuild_database.py`: imports locations into `fungi.db`
- `app.py`: displays bag/location data on the website

## Install

Copy all four files into the fungi project folder. Back up the old scripts first:

```bash
cp app.py app_before_locations.py
cp rebuild_database.py rebuild_database_before_locations.py
cp fungi.db fungi_before_locations.db
```

Then replace `app.py` and `rebuild_database.py`.

## Assign one isolate

```bash
python plate_location_manager.py assign B1005
```

You may enter either a sequencing ID or plate ID.

Categories:

- `N`: not growing, e.g. `01N`
- `S`: species bag, e.g. `S-Colletotrichum-coccodes`
- `T`: to be sequenced, e.g. `01T`
- `P`: failed PCR, e.g. `01P`
- `D`: double/duplicate, e.g. `01D`
- `G`: growing, e.g. `01G`
- `O`: other

## Process many plates

```bash
python plate_location_manager.py interactive
```

## Check a location

```bash
python plate_location_manager.py show B1005
```

## List bags

```bash
python plate_location_manager.py bags
```

## List isolates that have no location

```bash
python plate_location_manager.py unassigned
```

## Update the website

After assigning locations:

```bash
python rebuild_database.py
python app.py
```

The website will display bag code, category, container, position, and location notes.

## Push online

```bash
git add app.py rebuild_database.py plate_location_manager.py isolate_locations.csv fungi.db
git commit -m "Add isolate storage locations"
git push
```

Remember: edit location data locally. Render's filesystem is not permanent.
