SEQUENCING WORKFLOW WEBSITE INTEGRATION

These app.py and rebuild_database.py files were made from the exact versions you uploaded.

IMPORTANT:
- If you already have sequencing_workflow.csv with real entries, KEEP YOUR EXISTING CSV.
- Do not replace it with the empty example CSV in this package.

Install:
1. Back up current files:
   cp app.py app_before_workflow.py
   cp rebuild_database.py rebuild_database_before_workflow.py
   cp fungi.db fungi_before_workflow.db

2. Replace app.py and rebuild_database.py with the new versions.

3. Make sure sequencing_workflow.csv is in the same project folder.

4. Run:
   python rebuild_database.py

5. Test:
   python app.py

6. Open the home page and click "Sequencing Workflow".

What was added:
- sequencing_workflow table in fungi.db
- import of sequencing_workflow.csv during rebuild
- /sequencing overview page
- search/filter by workflow state
- workflow section on individual isolate pages
- "Reference for" links on reference isolates

The Linux workflow manager remains the data-entry tool.
