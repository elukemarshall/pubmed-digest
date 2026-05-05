# Benchmarks (`evals/`)

`pubmed-digest` uses frozen fixtures for benchmark reproducibility. The first
implementation slice sets up the fixture inventory and validation path before
any live PubMed capture or live LLM comparison work begins.

## What is in place now

- `fixtures/queries.jsonl` defines the benchmark query set scaffold.
- `fixtures/golden/*.json` defines one golden-case file per query.
- `fixtures/pubmed_responses/<query_id>/` reserves a directory for frozen
  ESearch, ESummary, and EFetch payloads captured later.
- `benchmark.py` loads those files and writes a dated fixture-readiness report
  to `evals/results/`.

## Running

```bash
UV_CACHE_DIR=.uv-cache uv run python -m evals.benchmark
```

The report is intentionally boring right now: it tells you how many query
fixtures exist, whether the golden files are still scaffold placeholders, and
how many captured PubMed response files each query has.

## Next upgrade path

1. Capture live PubMed fixtures into `fixtures/pubmed_responses/`.
2. Replace scaffold golden cases with grounded relevant PMIDs, key facts, and
   abstention targets.
3. Add LiteLLM + Instructor when the repo is ready for model-backed runs.
4. Extend `benchmark.py` from fixture inventory into the real four-axis eval
   described in ADR-0004.
