# Frozen Fixtures

This directory is the benchmark scaffold for `pubmed-digest`.

Structure:

- `queries.jsonl` — one benchmark query per line.
- `golden/` — one JSON file per query ID with the expected scoring targets.
- `pubmed_responses/<query_id>/` — captured ESearch, ESummary, and EFetch
  payloads keyed by request hash once live fixture capture begins.

Current status:

- Query definitions are present.
- Golden files are scaffold placeholders.
- PubMed response directories are empty by design in this first
  implementation slice.
