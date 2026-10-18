from flask import Flask, render_template_string, request, abort, url_for, redirect
import csv
import sqlite3
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "fungi.db")
ANNOTATIONS_CSV = Path(os.path.dirname(__file__)) / "isolate_annotations.csv"

BASE_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 30px; }
    a { text-decoration: none; }
    table { border-collapse: collapse; width: 100%; max-width: 1300px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f3f3f3; }
    input[type='text'], select, textarea { padding: 8px; width: 100%; max-width: 650px; box-sizing: border-box; }
    button { padding: 8px 12px; cursor: pointer; }
    .toplinks { margin-bottom: 20px; }
    .toplinks a { margin-right: 15px; }
    .small { color: #666; font-size: 0.95em; }
    .cultivar-list { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
    .cultivar-card { display: inline-block; padding: 18px 24px; border: 1px solid #ccc; border-radius: 10px; color: black; background: #f8f8f8; min-width: 180px; }
    .cultivar-card:hover { background: #efefef; }
    .searchbar { margin: 18px 0; }
    .searchbar input { width: 360px; }
    .badge { display: inline-block; background: #f3f3f3; border: 1px solid #ddd; border-radius: 999px; padding: 4px 10px; margin-right: 8px; }
    .status-active { background: #e8f5e9; }
    .status-inactive { background: #ffebee; }
    .status-slow { background: #fff8e1; }
    .status-unknown { background: #f3f3f3; }
</style>
"""

HOME_HTML = """
<!doctype html>
<html><head><title>Fungi Database</title>{{ style|safe }}</head>
<body>
<h1>Fungi Isolates</h1>
<div><span class="badge">{{ total }} active isolates</span><span class="badge">{{ identified }} with species</span><span class="badge">{{ located }} assigned locations</span></div>
<form class="searchbar" action="{{ url_for('search') }}" method="get">
<input name="q" placeholder="Search ID, species, bag, location" value=""><button type="submit">Search</button>
</form>
<h2>Cultivars</h2>
<div class="cultivar-list">
{% for c in cultivars %}
<a class="cultivar-card" href="{{ url_for('cultivar_page', cultivar=c.cultivar) }}"><strong>{{ c.cultivar|capitalize }}</strong><br><span class="small">{{ c.count }} isolates</span></a>
{% endfor %}
</div>
</body></html>
"""

CULTIVAR_HTML = """
<!doctype html>
<html><head><title>{{ cultivar|capitalize }} - Fungi Database</title>{{ style|safe }}</head>
<body>
<div class="toplinks"><a href="{{ url_for('home') }}">Home</a></div>
<h1>{{ cultivar|capitalize }}</h1>
<p>{{ isolates|length }} active isolates</p>
<table>
<tr><th>Seq ID</th><th>Plate ID</th><th>Field</th><th>Type</th><th>Layer</th><th>Media</th><th>Culture status</th><th>Species</th><th>Bag</th></tr>
{% for row in isolates %}
<tr>
<td><a href="{{ url_for('isolate_page', seq_id=row.seq_id) }}">{{ row.seq_id }}</a></td>
<td>{{ row.final_id or "" }}</td><td>{{ row.field or "" }}</td><td>{{ row.type or "" }}</td><td>{{ row.layer or "" }}</td><td>{{ row.media or "" }}</td>
<td>{{ row.culture_status or "not tested" }}</td><td>{{ row.species or "" }}</td><td>{{ row.bag_code or "" }}</td>
</tr>
{% endfor %}
</table>
</body></html>
"""

ISOLATE_HTML = """
<!doctype html>
<html><head><title>{{ isolate.seq_id }} - Fungi Database</title>{{ style|safe }}</head>
<body>
<div class="toplinks">
<a href="{{ url_for('home') }}">Home</a>
{% if isolate.cultivar %}<a href="{{ url_for('cultivar_page', cultivar=isolate.cultivar) }}">Back to {{ isolate.cultivar|capitalize }}</a>{% endif %}
<a href="{{ url_for('edit_isolate', seq_id=isolate.seq_id) }}">Edit annotation</a>
</div>
<h1>{{ isolate.seq_id }}</h1>
<table>
<tr><th>Sequencing ID</th><td>{{ isolate.seq_id or "" }}</td></tr>
<tr><th>Plate ID</th><td>{{ isolate.final_id or "" }}</td></tr>
<tr><th>Original ID</th><td>{{ isolate.original_id or "" }}</td></tr>
<tr><th>Cultivar</th><td>{{ isolate.cultivar or "" }}</td></tr>
<tr><th>Field</th><td>{{ isolate.field or "" }}</td></tr>
<tr><th>Type</th><td>{{ isolate.type or "" }}</td></tr>
<tr><th>Layer</th><td>{{ isolate.layer or "" }}</td></tr>
<tr><th>Media</th><td>{{ isolate.media or "" }}</td></tr>
<tr><th>Replicate</th><td>{{ isolate.replicate or "" }}</td></tr>
<tr><th>Culture Status</th><td>{{ isolate.culture_status or "not tested" }}</td></tr>
<tr><th>Species</th><td>{{ isolate.species or "" }}</td></tr>
<tr><th>Bag Code</th><td>{{ isolate.bag_code or "" }}</td></tr>
<tr><th>Location Category</th><td>{{ isolate.location_category or "" }}</td></tr>
<tr><th>Species Group</th><td>{{ isolate.species_group or "" }}</td></tr>
<tr><th>Container / Freezer / Box</th><td>{{ isolate.storage_container or "" }}</td></tr>
<tr><th>Position</th><td>{{ isolate.storage_position or "" }}</td></tr>
<tr><th>Location Notes</th><td>{{ isolate.location_notes or "" }}</td></tr>
<tr><th>Location Updated</th><td>{{ isolate.location_updated_at or "" }}</td></tr>
<tr><th>BLAST Top Hit</th><td>{{ isolate.blast_top_hit or "" }}</td></tr>
<tr><th>BLAST Accession</th><td>{{ isolate.blast_accession or "" }}</td></tr>
<tr><th>BLAST Identity</th><td>{{ isolate.blast_identity or "" }}</td></tr>
<tr><th>BLAST Query Coverage</th><td>{{ isolate.blast_query_coverage or "" }}</td></tr>
<tr><th>BLAST E-value</th><td>{{ isolate.blast_evalue or "" }}</td></tr>
<tr><th>FASTA Path</th><td>{{ isolate.fasta_path or "" }}</td></tr>
<tr><th>FASTA Sequence</th><td style="white-space: pre-wrap;">{{ isolate.fasta_sequence or "" }}</td></tr>
<tr><th>Image Path</th><td>{{ isolate.image_path or "" }}</td></tr>
<tr><th>Notes</th><td style="white-space: pre-wrap;">{{ isolate.notes or "" }}</td></tr>
</table>
</body></html>
"""

SEARCH_HTML = """
<!doctype html>
<html><head><title>Search - Fungi Database</title>{{ style|safe }}</head>
<body>
<div class="toplinks"><a href="{{ url_for('home') }}">Home</a></div>
<h1>Search Results</h1>
<form class="searchbar" action="{{ url_for('search') }}" method="get"><input name="q" value="{{ q }}"><button type="submit">Search</button></form>
<p>{{ results|length }} result(s)</p>
<table>
<tr><th>Seq ID</th><th>Plate ID</th><th>Cultivar</th><th>Status</th><th>Species</th><th>Bag</th><th>Container</th></tr>
{% for row in results %}
<tr>
<td><a href="{{ url_for('isolate_page', seq_id=row.seq_id) }}">{{ row.seq_id }}</a></td>
<td>{{ row.final_id or "" }}</td><td>{{ row.cultivar or "" }}</td><td>{{ row.culture_status or "not tested" }}</td>
<td>{{ row.species or "" }}</td><td>{{ row.bag_code or "" }}</td><td>{{ row.storage_container or "" }}</td>
</tr>
{% endfor %}
</table>
</body></html>
"""


def get_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def update_annotation_csv(seq_id, updates):
    fields = [
        "seq_id", "culture_status", "species", "blast_top_hit", "blast_accession",
        "blast_identity", "blast_query_coverage", "blast_evalue", "fasta_path",
        "fasta_sequence", "image_path", "notes",
    ]
    rows = {}
    if ANNOTATIONS_CSV.exists():
        with ANNOTATIONS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                key = (row.get("seq_id") or "").strip()
                if key:
                    rows[key] = {field: row.get(field, "") for field in fields}
    row = rows.get(seq_id, {field: "" for field in fields})
    row["seq_id"] = seq_id
    row.update({key: value or "" for key, value in updates.items()})
    rows[seq_id] = row
    with ANNOTATIONS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow(rows[key])


@app.route("/")
def home():
    conn = get_connection()
    cur = conn.cursor()
    cultivars = cur.execute("SELECT cultivar, COUNT(*) count FROM isolates GROUP BY cultivar ORDER BY cultivar").fetchall()
    total = cur.execute("SELECT COUNT(*) FROM isolates").fetchone()[0]
    identified = cur.execute("SELECT COUNT(*) FROM isolates WHERE species IS NOT NULL").fetchone()[0]
    located = cur.execute("SELECT COUNT(*) FROM isolates WHERE bag_code IS NOT NULL").fetchone()[0]
    conn.close()
    return render_template_string(HOME_HTML, style=BASE_STYLE, cultivars=cultivars, total=total, identified=identified, located=located)


@app.route("/cultivar/<cultivar>")
def cultivar_page(cultivar):
    conn = get_connection()
    isolates = conn.execute("""
        SELECT seq_id, final_id, field, type, layer, media, culture_status, species, bag_code
        FROM isolates WHERE lower(cultivar) = lower(?) ORDER BY seq_id
    """, (cultivar,)).fetchall()
    conn.close()
    if not isolates:
        abort(404)
    return render_template_string(CULTIVAR_HTML, style=BASE_STYLE, cultivar=cultivar, isolates=isolates)


@app.route("/isolate/<seq_id>")
def isolate_page(seq_id):
    conn = get_connection()
    isolate = conn.execute("SELECT * FROM isolates WHERE seq_id = ?", (seq_id,)).fetchone()
    conn.close()
    if isolate is None:
        abort(404)
    return render_template_string(ISOLATE_HTML, style=BASE_STYLE, isolate=isolate)


@app.route("/isolate/<seq_id>/edit", methods=["GET", "POST"])
def edit_isolate(seq_id):
    conn = get_connection()
    isolate = conn.execute("SELECT * FROM isolates WHERE seq_id = ?", (seq_id,)).fetchone()
    if isolate is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        updates = {
            "culture_status": request.form.get("culture_status"),
            "species": request.form.get("species"),
            "blast_top_hit": request.form.get("blast_top_hit"),
            "blast_accession": request.form.get("blast_accession"),
            "blast_identity": request.form.get("blast_identity"),
            "blast_query_coverage": request.form.get("blast_query_coverage"),
            "blast_evalue": request.form.get("blast_evalue"),
            "fasta_path": request.form.get("fasta_path"),
            "fasta_sequence": request.form.get("fasta_sequence"),
            "image_path": request.form.get("image_path"),
            "notes": request.form.get("notes"),
        }
        conn.execute("""
            UPDATE isolates SET culture_status=?, species=?, blast_top_hit=?,
            blast_accession=?, blast_identity=?, blast_query_coverage=?,
            blast_evalue=?, fasta_path=?, fasta_sequence=?, image_path=?, notes=?
            WHERE seq_id=?
        """, (
            updates["culture_status"] or None, updates["species"] or None,
            updates["blast_top_hit"] or None, updates["blast_accession"] or None,
            updates["blast_identity"] or None, updates["blast_query_coverage"] or None,
            updates["blast_evalue"] or None, updates["fasta_path"] or None,
            updates["fasta_sequence"] or None, updates["image_path"] or None,
            updates["notes"] or None, seq_id,
        ))
        conn.commit()
        conn.close()
        update_annotation_csv(seq_id, updates)
        return redirect(url_for("isolate_page", seq_id=seq_id))

    conn.close()
    return render_template_string("""
    <!doctype html><html><head><title>Edit {{ isolate.seq_id }}</title>{{ style|safe }}</head><body>
    <p><a href="{{ url_for('isolate_page', seq_id=isolate.seq_id) }}">Cancel</a></p>
    <h1>Edit {{ isolate.seq_id }}</h1>
    <form method="post">
        <p>Culture Status:<br>
        <select name="culture_status">
            {% for value in statuses %}
            <option value="{{ value }}" {% if isolate.culture_status == value or (value == "not tested" and not isolate.culture_status) %}selected{% endif %}>{{ value }}</option>
            {% endfor %}
        </select></p>
        <p>Species:<br><input name="species" value="{{ isolate.species or '' }}"></p>
        <p>BLAST Top Hit:<br><input name="blast_top_hit" value="{{ isolate.blast_top_hit or '' }}"></p>
        <p>BLAST Accession:<br><input name="blast_accession" value="{{ isolate.blast_accession or '' }}"></p>
        <p>BLAST Identity:<br><input name="blast_identity" value="{{ isolate.blast_identity or '' }}"></p>
        <p>BLAST Query Coverage:<br><input name="blast_query_coverage" value="{{ isolate.blast_query_coverage or '' }}"></p>
        <p>BLAST E-value:<br><input name="blast_evalue" value="{{ isolate.blast_evalue or '' }}"></p>
        <p>FASTA Path:<br><input name="fasta_path" value="{{ isolate.fasta_path or '' }}"></p>
        <p>FASTA Sequence:<br><textarea name="fasta_sequence" rows="8">{{ isolate.fasta_sequence or '' }}</textarea></p>
        <p>Image Path:<br><input name="image_path" value="{{ isolate.image_path or '' }}"></p>
        <p>Notes:<br><textarea name="notes" rows="6">{{ isolate.notes or '' }}</textarea></p>
        <button type="submit">Save changes</button>
    </form></body></html>
    """, style=BASE_STYLE, isolate=isolate, statuses=[
        "not tested", "active", "inactive after first plating",
        "inactive after transfer", "slow growth", "contaminated", "lost"
    ])


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    conn = get_connection()
    if q:
        like = f"%{q}%"
        results = conn.execute("""
            SELECT seq_id, final_id, cultivar, culture_status, species, bag_code, storage_container
            FROM isolates
            WHERE seq_id LIKE ? OR final_id LIKE ? OR original_id LIKE ?
               OR cultivar LIKE ? OR species LIKE ? OR blast_top_hit LIKE ?
               OR bag_code LIKE ? OR storage_container LIKE ? OR location_notes LIKE ?
            ORDER BY seq_id
        """, (like, like, like, like, like, like, like, like, like)).fetchall()
    else:
        results = []
    conn.close()
    return render_template_string(SEARCH_HTML, style=BASE_STYLE, q=q, results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
