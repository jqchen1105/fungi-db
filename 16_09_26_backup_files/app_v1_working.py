from flask import Flask, render_template_string, request, abort, url_for, redirect
import sqlite3
import os

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "fungi.db")

BASE_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 30px; }
    a { text-decoration: none; }
    table { border-collapse: collapse; width: 100%; max-width: 1200px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f3f3f3; }
    input[type='text'], select { padding: 8px; width: 260px; }
    button { padding: 8px 12px; cursor: pointer; }
    .toplinks { margin-bottom: 20px; }
    .toplinks a { margin-right: 15px; }
    .small { color: #666; font-size: 0.95em; }
    .cultivar-list { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
    .cultivar-card { display: inline-block; padding: 18px 24px; border: 1px solid #ccc; border-radius: 10px; color: black; background: #f8f8f8; min-width: 180px; }
    .cultivar-card:hover { background: #efefef; }
    .searchbar { margin: 18px 0; }
    .badge { display: inline-block; background: #f3f3f3; border: 1px solid #ddd; border-radius: 999px; padding: 4px 10px; margin-right: 8px; }
</style>
"""

HOME_HTML = """
<!doctype html>
<html>
<head>
    <title>Fungi Database</title>
    {{ style|safe }}
</head>
<body>
    <h1>Fungi Isolates</h1>

    <div>
        <span class="badge">{{ total }} active isolates</span>
        <span class="badge">{{ identified }} with species</span>
    </div>

    <form class="searchbar" action="{{ url_for('search') }}" method="get">
        <input name="q" placeholder="Search seq_id, plate ID, cultivar, species" value="">
        <button type="submit">Search</button>
    </form>

    <h2 style="margin-top: 30px;">Cultivars</h2>
    <div class="cultivar-list">
        {% for c in cultivars %}
        <a class="cultivar-card" href="{{ url_for('cultivar_page', cultivar=c.cultivar) }}">
            <strong>{{ c.cultivar|capitalize }}</strong><br>
            <span class="small">{{ c.count }} isolates</span>
        </a>
        {% endfor %}
    </div>
</body>
</html>
"""

CULTIVAR_HTML = """
<!doctype html>
<html>
<head>
    <title>{{ cultivar|capitalize }} - Fungi Database</title>
    {{ style|safe }}
</head>
<body>
    <div class="toplinks"><a href="{{ url_for('home') }}">Home</a></div>
    <h1>{{ cultivar|capitalize }}</h1>
    <p>{{ isolates|length }} active isolates</p>

    <form class="searchbar" action="{{ url_for('search') }}" method="get">
        <input name="q" placeholder="Search seq_id, plate ID, cultivar, species" value="">
        <button type="submit">Search</button>
    </form>

    <table>
        <tr>
            <th>Seq ID</th><th>Plate ID</th><th>Field</th><th>Type</th><th>Layer</th><th>Media</th><th>Species</th>
        </tr>
        {% for row in isolates %}
        <tr>
            <td><a href="{{ url_for('isolate_page', seq_id=row.seq_id) }}">{{ row.seq_id }}</a></td>
            <td>{{ row.final_id or "" }}</td>
            <td>{{ row.field or "" }}</td>
            <td>{{ row.type or "" }}</td>
            <td>{{ row.layer or "" }}</td>
            <td>{{ row.media or "" }}</td>
            <td>{{ row.species or "" }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

ISOLATE_HTML = """
<!doctype html>
<html>
<head>
    <title>{{ isolate.seq_id }} - Fungi Database</title>
    {{ style|safe }}
</head>
<body>
    <div class="toplinks">
        <a href="{{ url_for('home') }}">Home</a>
        {% if isolate.cultivar %}<a href="{{ url_for('cultivar_page', cultivar=isolate.cultivar) }}">Back to {{ isolate.cultivar|capitalize }}</a>{% endif %}
<a href="{{ url_for('edit_isolate', seq_id=isolate.seq_id) }}">Edit</a>
    </div>

    <h1>{{ isolate.seq_id }}</h1>

    <table>
        <tr><th>Sequencing ID</th><td>{{ isolate.seq_id or "" }}</td></tr>
        <tr><th>Plate ID</th><td>{{ isolate.final_id or "" }}</td></tr>
        <tr><th>Original ID</th><td>{{ isolate.original_id or "" }}</td></tr>
        <tr><th>Base ID</th><td>{{ isolate.base_id or "" }}</td></tr>
        <tr><th>Parent ID</th><td>{{ isolate.parent_id or "" }}</td></tr>
        <tr><th>Cultivar Code</th><td>{{ isolate.cultivar_code or "" }}</td></tr>
        <tr><th>Cultivar</th><td>{{ isolate.cultivar or "" }}</td></tr>
        <tr><th>Field</th><td>{{ isolate.field or "" }}</td></tr>
        <tr><th>Ignored No</th><td>{{ isolate.ignored_no or "" }}</td></tr>
        <tr><th>Type</th><td>{{ isolate.type or "" }}</td></tr>
        <tr><th>Layer</th><td>{{ isolate.layer or "" }}</td></tr>
        <tr><th>Media</th><td>{{ isolate.media or "" }}</td></tr>
        <tr><th>Replicate</th><td>{{ isolate.replicate or "" }}</td></tr>
        <tr><th>Isolate No</th><td>{{ isolate.isolate_no or "" }}</td></tr>
        <tr><th>Assigned Isolate No</th><td>{{ isolate.assigned_isolate_no or "" }}</td></tr>
        <tr><th>Changed</th><td>{{ isolate.changed or "" }}</td></tr>
        <tr><th>Status</th><td>{{ isolate.status or "" }}</td></tr>
        <tr><th>Reason</th><td>{{ isolate.reason or "" }}</td></tr>
        <tr><th>Species</th><td>{{ isolate.species or "" }}</td></tr>
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
</body>
</html>
"""

SEARCH_HTML = """
<!doctype html>
<html>
<head>
    <title>Search - Fungi Database</title>
    {{ style|safe }}
</head>
<body>
    <div class="toplinks"><a href="{{ url_for('home') }}">Home</a></div>
    <h1>Search Results</h1>

    <form class="searchbar" action="{{ url_for('search') }}" method="get">
        <input name="q" placeholder="Search seq_id, plate ID, cultivar, species" value="{{ q }}">
        <button type="submit">Search</button>
    </form>

    <p>{{ results|length }} result(s)</p>
    <table>
        <tr>
            <th>Seq ID</th><th>Plate ID</th><th>Cultivar</th><th>Field</th><th>Type</th><th>Layer</th><th>Media</th><th>Species</th>
        </tr>
        {% for row in results %}
        <tr>
            <td><a href="{{ url_for('isolate_page', seq_id=row.seq_id) }}">{{ row.seq_id }}</a></td>
            <td>{{ row.final_id or "" }}</td>
            <td>{{ row.cultivar or "" }}</td>
            <td>{{ row.field or "" }}</td>
            <td>{{ row.type or "" }}</td>
            <td>{{ row.layer or "" }}</td>
            <td>{{ row.media or "" }}</td>
            <td>{{ row.species or "" }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""


def get_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT cultivar, COUNT(*) AS count
        FROM isolates
        WHERE status = 'active'
        GROUP BY cultivar
        ORDER BY cultivar
    """)
    cultivars = cur.fetchall()
    total = cur.execute("SELECT COUNT(*) FROM isolates WHERE status = 'active'").fetchone()[0]
    identified = cur.execute("SELECT COUNT(*) FROM isolates WHERE status = 'active' AND species IS NOT NULL").fetchone()[0]
    conn.close()
    return render_template_string(HOME_HTML, style=BASE_STYLE, cultivars=cultivars, total=total, identified=identified)


@app.route("/cultivar/<cultivar>")
def cultivar_page(cultivar):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT seq_id, final_id, field, type, layer, media, species, cultivar
        FROM isolates
        WHERE lower(cultivar) = lower(?) AND status = 'active'
        ORDER BY seq_id
    """, (cultivar,))
    isolates = cur.fetchall()
    conn.close()
    if not isolates:
        abort(404)
    return render_template_string(CULTIVAR_HTML, style=BASE_STYLE, cultivar=cultivar, isolates=isolates)


@app.route("/isolate/<seq_id>")
def isolate_page(seq_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM isolates WHERE seq_id = ? AND status = 'active'", (seq_id,))
    isolate = cur.fetchone()
    conn.close()
    if isolate is None:
        abort(404)
    return render_template_string(ISOLATE_HTML, style=BASE_STYLE, isolate=isolate)

@app.route("/isolate/<seq_id>/edit", methods=["GET", "POST"])
def edit_isolate(seq_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM isolates WHERE seq_id = ? AND status = 'active'", (seq_id,))
    isolate = cur.fetchone()

    if isolate is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        cur.execute("""
            UPDATE isolates
            SET
                species = ?,
                blast_top_hit = ?,
                blast_accession = ?,
                blast_identity = ?,
                blast_query_coverage = ?,
                blast_evalue = ?,
                fasta_path = ?,
                fasta_sequence = ?,
                image_path = ?,
                notes = ?
            WHERE seq_id = ?
        """, (
            request.form.get("species") or None,
            request.form.get("blast_top_hit") or None,
            request.form.get("blast_accession") or None,
            request.form.get("blast_identity") or None,
            request.form.get("blast_query_coverage") or None,
            request.form.get("blast_evalue") or None,
            request.form.get("fasta_path") or None,
            request.form.get("fasta_sequence") or None,
            request.form.get("image_path") or None,
            request.form.get("notes") or None,
            seq_id,
        ))

        conn.commit()
        conn.close()
        return redirect(url_for("isolate_page", seq_id=seq_id))

    conn.close()

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <title>Edit {{ isolate.seq_id }}</title>
        <style>{{ style }}</style>
    </head>
    <body>
        <p>
            <a href="{{ url_for('isolate_page', seq_id=isolate.seq_id) }}">Cancel</a>
        </p>

        <h1>Edit {{ isolate.seq_id }}</h1>

        <form method="post">
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
        </form>
    </body>
    </html>
    """, style=BASE_STYLE, isolate=isolate)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    conn = get_connection()
    cur = conn.cursor()
    if q:
        like = f"%{q}%"
        cur.execute("""
            SELECT seq_id, final_id, cultivar, field, type, layer, media, species
            FROM isolates
            WHERE status = 'active'
              AND (
                seq_id LIKE ? OR final_id LIKE ? OR original_id LIKE ? OR
                cultivar LIKE ? OR species LIKE ? OR blast_top_hit LIKE ?
              )
            ORDER BY seq_id
        """, (like, like, like, like, like, like))
        results = cur.fetchall()
    else:
        results = []
    conn.close()
    return render_template_string(SEARCH_HTML, style=BASE_STYLE, q=q, results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
