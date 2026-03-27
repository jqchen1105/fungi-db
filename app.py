from flask import Flask, render_template_string, request, abort, url_for
import sqlite3

app = Flask(__name__)

DB = "fungi.db"

HOME_HTML = """
<!doctype html>
<html>
<head>
    <title>Fungi Database</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
        }
        .cultivar-list {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 20px;
        }
        .cultivar-card {
            display: inline-block;
            padding: 18px 24px;
            border: 1px solid #ccc;
            border-radius: 10px;
            text-decoration: none;
            color: black;
            background: #f8f8f8;
            min-width: 180px;
        }
        .cultivar-card:hover {
            background: #efefef;
        }
        .small {
            color: #666;
            font-size: 0.95em;
        }
        input[type="text"] {
            padding: 8px;
            width: 260px;
        }
        button {
            padding: 8px 12px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Fungi Isolates</h1>

    <form action="{{ url_for('search') }}" method="get">
        <input name="q" placeholder="Search seq_id or plate ID (e.g. A1002)" value="">
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
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 1100px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }
        th {
            background: #f3f3f3;
        }
        a {
            text-decoration: none;
        }
        .toplinks {
            margin-bottom: 20px;
        }
        .toplinks a {
            margin-right: 15px;
        }
        input[type="text"] {
            padding: 8px;
            width: 260px;
        }
        button {
            padding: 8px 12px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="toplinks">
        <a href="{{ url_for('home') }}">Home</a>
    </div>

    <h1>{{ cultivar|capitalize }}</h1>
    <p>{{ isolates|length }} isolates</p>

    <form action="{{ url_for('search') }}" method="get">
        <input name="q" placeholder="Search seq_id or plate ID" value="">
        <button type="submit">Search</button>
    </form>

    <table style="margin-top: 20px;">
        <tr>
            <th>Seq ID</th>
            <th>Plate ID</th>
            <th>Field</th>
            <th>Type</th>
            <th>Layer</th>
            <th>Media</th>
            <th>Species</th>
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
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
            max-width: 1000px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 900px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 10px;
            text-align: left;
            vertical-align: top;
        }
        th {
            width: 240px;
            background: #f3f3f3;
        }
        .toplinks {
            margin-bottom: 20px;
        }
        .toplinks a {
            margin-right: 15px;
        }
        .section {
            margin-top: 28px;
        }
    </style>
</head>
<body>
    <div class="toplinks">
        <a href="{{ url_for('home') }}">Home</a>
        <a href="{{ url_for('cultivar_page', cultivar=isolate.cultivar) }}">Back to {{ isolate.cultivar|capitalize }}</a>
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
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 1100px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }
        th {
            background: #f3f3f3;
        }
        .toplinks {
            margin-bottom: 20px;
        }
        .toplinks a {
            margin-right: 15px;
        }
        input[type="text"] {
            padding: 8px;
            width: 260px;
        }
        button {
            padding: 8px 12px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="toplinks">
        <a href="{{ url_for('home') }}">Home</a>
    </div>

    <h1>Search Results</h1>

    <form action="{{ url_for('search') }}" method="get">
        <input name="q" placeholder="Search seq_id or plate ID" value="{{ q }}">
        <button type="submit">Search</button>
    </form>

    <p style="margin-top: 20px;">{{ results|length }} result(s)</p>

    <table>
        <tr>
            <th>Seq ID</th>
            <th>Plate ID</th>
            <th>Cultivar</th>
            <th>Field</th>
            <th>Type</th>
            <th>Layer</th>
            <th>Media</th>
            <th>Species</th>
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
        GROUP BY cultivar
        ORDER BY cultivar
    """)
    cultivars = cur.fetchall()
    conn.close()
    return render_template_string(HOME_HTML, cultivars=cultivars)


@app.route("/cultivar/<cultivar>")
def cultivar_page(cultivar):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT seq_id, final_id, field, type, layer, media, species, cultivar
        FROM isolates
        WHERE lower(cultivar) = lower(?)
        ORDER BY seq_id
    """, (cultivar,))
    isolates = cur.fetchall()
    conn.close()

    if not isolates:
        abort(404)

    return render_template_string(CULTIVAR_HTML, cultivar=cultivar, isolates=isolates)


@app.route("/isolate/<seq_id>")
def isolate_page(seq_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM isolates
        WHERE seq_id = ?
    """, (seq_id,))
    isolate = cur.fetchone()
    conn.close()

    if isolate is None:
        abort(404)

    return render_template_string(ISOLATE_HTML, isolate=isolate)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    if q:
        cur.execute("""
            SELECT seq_id, final_id, cultivar, field, type, layer, media, species
            FROM isolates
            WHERE seq_id LIKE ? OR final_id LIKE ? OR cultivar LIKE ?
            ORDER BY seq_id
        """, (f"%{q}%", f"%{q}%", f"%{q}%"))
        results = cur.fetchall()
    else:
        results = []

    conn.close()

    return render_template_string(SEARCH_HTML, q=q, results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
