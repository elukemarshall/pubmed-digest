# pubmed-digest

[![CI](https://github.com/elukemarshall/pubmed-digest/actions/workflows/ci.yml/badge.svg)](https://github.com/elukemarshall/pubmed-digest/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A biotech literature summarization CLI. Queries PubMed, ranks results with
metadata-first retrieval, fetches abstracts only for the top-k papers, and
synthesizes per-paper cards plus a cross-paper digest with structured,
citation-grounded outputs. Multiple model backends are benchmarked on frozen
local fixtures.

> **Status:** Phase 1, Project 1 of a private biotech AI/ML curriculum.
> Design phase — SPEC and ADRs land before app code.

## Who this is for

Biotech researchers, BD analysts, and medical-affairs operators who triage
literature daily and want a faster path from a question to a structured,
cited summary than running a PubMed search and reading abstracts by hand.

## Why it matters

Manual literature triage is a major time cost in biotech knowledge work.
A small CLI that pre-ranks by metadata, fetches abstracts only for ranked
top-k, and produces structured per-paper cards with citations is designed
to turn a manual triage session into a short, reviewable artifact — and the
structured output makes the result reusable in downstream tools.

## Non-goals

- Patient-facing clinical decision support.
- Full-text PMC retrieval (abstract-grounded only in v1).
- A web UI — this is a CLI; a service comes later.
- Beating PaperQA2 on scientific QA — pubmed-digest is triage and
  summarization, not deep multi-document QA.

## Design documents

- [`docs/SPEC.md`](docs/SPEC.md) — goals, non-goals, architecture, scope.
- [`docs/adr/0001-metadata-first-retrieval.md`](docs/adr/0001-metadata-first-retrieval.md)
- [`docs/adr/0002-structured-output-grounding.md`](docs/adr/0002-structured-output-grounding.md)
- [`docs/adr/0003-model-routing-policy.md`](docs/adr/0003-model-routing-policy.md)
- [`docs/adr/0004-reproducible-benchmark-methodology.md`](docs/adr/0004-reproducible-benchmark-methodology.md)
- [`docs/adr/0005-toolchain.md`](docs/adr/0005-toolchain.md) — toolchain
  inherited from the Fabrica template.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . --fix
uv run ruff format .
uv run pyright
uv run pre-commit run --all-files
```

## Container smoke test

```bash
docker build -t pubmed-digest .
docker run --rm pubmed-digest
```

## Safety and limitations

This tool is for research and triage assistance only. It is not a
diagnostic instrument and is not safe for patient-facing clinical use.
LLM-generated summaries can hallucinate — every claim in the output is
grounded to a PubMed citation and the source abstract should be read
before relying on a finding. See [`docs/SPEC.md`](docs/SPEC.md) for the
full safety/limitations frame.

## License

MIT — see [`LICENSE`](LICENSE).
