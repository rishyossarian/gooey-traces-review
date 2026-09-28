#!/usr/bin/env python3
"""Load error_discovery_data/*.json into Supabase as the public example workspace.

Usage:  DATABASE_URL=... python3 supabase/load_example.py <passcode>
Re-running replaces the example's data with the current local files (same workspace id).
Needs psycopg2 (e.g. run with ~/user-funnel-tracker/.venv/bin/python).
"""
import json
import sys
import os
from pathlib import Path

import psycopg2

NAME = "Gooey Essay Traces: Error Analysis for AI Evals"
DATA = Path(__file__).resolve().parent.parent / "error_discovery_data"
KINDS = ["samples", "annotations", "graph", "patterns", "suggestions"]

passcode = sys.argv[1]
conn = psycopg2.connect(os.environ["DATABASE_URL"])
with conn, conn.cursor() as cur:
    cur.execute("select id from trace_workspaces where is_example limit 1")
    row = cur.fetchone()
    if row:
        ws = row[0]
        cur.execute("update trace_workspaces set name = %s where id = %s", (NAME, ws))
    else:
        cur.execute("insert into trace_workspaces (name, is_example) values (%s, true) returning id", (NAME,))
        ws = cur.fetchone()[0]
    cur.execute(
        "insert into trace_workspace_secrets values (%s, extensions.crypt(%s, extensions.gen_salt('bf'))) "
        "on conflict (workspace_id) do update set passcode_hash = excluded.passcode_hash",
        (ws, passcode),
    )
    for kind in KINDS:
        data = json.loads((DATA / f"{kind}.json").read_text())
        cur.execute(
            "insert into trace_workspace_data (workspace_id, kind, data) values (%s, %s, %s) "
            "on conflict (workspace_id, kind) do update set data = excluded.data, updated_at = now()",
            (ws, kind, json.dumps(data)),
        )
print(f"Example workspace {ws} loaded.")
