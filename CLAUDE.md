# Trace Error Analysis (Gooey Essay Traces example)

Rishita's tool for error analysis on LLM traces (open coding → axial coding → counting failure modes), following Hamel Husain's evals method. Originally built for Gooey's essay-writing traces; now public so anyone can upload their own traces and annotate them. The Gooey traces stay as a view-only example.

## Two ways it runs
1. **Hosted (public):** `app.html` on GitHub Pages; data in Supabase. Turned on by filling in `HOSTED = { url, key }` near the top of the `<script>` in `app.html` (Supabase project URL + publishable/anon key; both are safe to publish).
   - Workspaces: the example (`is_example`) plus one per visitor upload. Anyone can view; editing needs that workspace's passcode (checked server-side in Supabase functions, see `supabase/schema.sql`).
   - Links: `?w=<workspace id>` opens a specific workspace.
2. **Local:** `python3 server.py` → http://127.0.0.1:8934/ (reads/writes `error_discovery_data/*.json`). Used when `HOSTED.url` is empty. Has a "Reset for demo" button (local only).

## Files
- `app.html`: the whole frontend. Tabs: Article (highlight to annotate), Map, Progress, Axial Codes + pivot table.
- `server.py`: local-only server. `restore_backup.py`: restores local demo-reset backups.
- `build_data.py`: turns `~/Downloads/traces.json` into `samples.json`/`graph.json` (local). The hosted upload does the same in the browser (`buildWorkspaceData` in `app.html`).
- `error_discovery_data/`: the Gooey example data. `annotations.json` is Rishita's real work.
- `supabase/schema.sql`: tables, access rules and passcode-checking functions. Re-runnable.
- `supabase/load_example.py <passcode>`: pushes the local example JSON into Supabase (overwrites the hosted example's data; hosted edits to the example would be lost, so pull those first).

## Gotchas
- Uploaded traces are shown to other visitors, so anything rendered with `innerHTML` must go through `escapeHtml`.
- "AI suggestions" were written into `suggestions.json` by a Claude session watching the annotations; the app doesn't generate them itself.
- Never use trycloudflare quick tunnels; they die when the laptop sleeps.

## Working with Rishita
She skims: lead with the answer or link, keep it short. Light, low-contrast colours; plain over ornate. Batch UI changes; after any change, reload and check it yourself before saying it's done.
