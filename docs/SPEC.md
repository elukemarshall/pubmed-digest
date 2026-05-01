# pubmed-digest — Design Specification

**Status:** Draft (design phase, no app code yet)
**Date:** 2026-05-01
**Author:** Luke Marshall

> This document is the design source-of-truth for `pubmed-digest`. The
> four ADRs in `docs/adr/` make the load-bearing decisions; this SPEC
> is the readable overview that ties them together. Any divergence
> between SPEC and ADR is resolved in favor of the ADR.

---

## 1. Project context

`pubmed-digest` is **Phase 1, Project 1** of a private biotech AI/ML
curriculum.

- **Phase:** 1 — Biotech tools and API fluency.
- **Project type:** engineering-first repo.
- **Phase window (pacing guide):** Weeks 3–5, 2026-05-06 → 2026-05-27.
- **Spawned from:** the `fabrica` Python template.
- **External baselines to know before coding:** PaperQA2 (scientific
  RAG), BioMCP (biomedical MCP), NCBI E-utilities, Europe PMC,
  Semantic Scholar.

---

## 2. Problem statement

Biotech researchers, BD analysts, and medical-affairs operators run
the same workflow many times a week: take a question, search PubMed,
skim 20–50 abstracts, and produce a structured summary with
citations. The friction is not the LLM; it is the manual, repetitive
ranking and reading.

A small CLI that does the **metadata-first ranking + structured,
citation-grounded summarization** in one command is designed to turn a
manual triage session into a short, reviewable artifact.

The output must be:

- **structured** — Markdown or JSON, schema-validated;
- **grounded** — every claim cites a PubMed PMID from the run's
  retrieved set;
- **honest** — abstains rather than confabulating when abstracts do
  not support an answer;
- **reproducible** — deterministic given the same fixtures and pinned
  model IDs.

---

## 3. Target user

Primary users:

- **Biotech researchers** doing literature triage on a target,
  mechanism, or indication.
- **BD / competitive intelligence analysts** monitoring publications
  in a therapeutic area.
- **Medical-affairs operators** generating evidence briefs.

Secondary user:

- The author, as a tool used inside other curriculum projects (Phase 2
  agents will likely import the retrieval client).

This tool is **not** for patient-facing clinical decision support and
is **not** for end users without biomedical literacy. The output
assumes the reader can verify a citation against the source abstract.

---

## 4. Goals

1. Ship a polished, typed, tested, benchmarked Python CLI that takes a
   biomedical question and produces a structured digest.
2. Demonstrate metadata-first retrieval over the NCBI E-utilities
   stack: ESearch → ESummary → ranked top-k → EFetch.
3. Demonstrate provider-agnostic LLM use with structured outputs and
   post-generation grounding verification.
4. Demonstrate a reproducible multi-model benchmark with fixtures,
   committed reports, and a clear switching rule.
5. Hit Phase 1's production drill: Dockerfile, structured logs,
   rate-limit + retry + cache layer, documented failure modes.

---

## 5. Non-goals

- **Patient-facing clinical decision support.** Disclaimed in the
  README and surfaced in the CLI on first run.
- **Full-text PMC retrieval.** v1 grounds on abstracts only.
- **A web UI / hosted service.** This is a CLI. Service-shaped work is
  a Phase 2 project.
- **Beating PaperQA2 on scientific QA.** Different unit of work — this
  is triage, not deep multi-document QA.
- **A vector database / embedding index.** Deferred to a later
  iteration only if the metadata-only ranker proves insufficient on
  the benchmark.
- **Cross-source enrichment beyond optional Europe PMC / Semantic
  Scholar hooks.** PubMed is the source of truth for v1.

---

## 6. Architecture

### 6.1 High-level pipeline

```
┌────────────┐    ┌──────────┐    ┌──────────────┐    ┌────────┐    ┌──────────┐
│ User query │───▶│ ESearch  │───▶│ ESummary +   │───▶│ EFetch │───▶│ LLM:     │
│ (CLI)      │    │ (PMIDs)  │    │ rank top_k   │    │ (k abs)│    │ per-card │
└────────────┘    └──────────┘    └──────────────┘    └────────┘    └─────┬────┘
                                                                          │
                                                                          ▼
                                                                    ┌─────────────┐
                                                                    │ LLM:        │
                                                                    │ synthesis   │
                                                                    │ (1 call)    │
                                                                    └──────┬──────┘
                                                                           │
                                                                           ▼
                                                                    ┌─────────────┐
                                                                    │ Grounding   │
                                                                    │ verifier    │
                                                                    └──────┬──────┘
                                                                           │
                                                            ┌──────────────┴────────────┐
                                                            ▼                           ▼
                                                      Markdown export             JSON export
```

Decisions backing this shape:

- **ADR-0001** — metadata-first retrieval (why ESummary is between
  ESearch and EFetch; why the ranker is deterministic; rate-limit /
  cache / failure-mode rules).
- **ADR-0002** — structured-output schemas, citation-first grounding,
  closed-set citation rule, and the post-generation verifier.
- **ADR-0003** — LiteLLM + Instructor; two roles (`card`,
  `synthesis`); `models.toml` source of truth for IDs.
- **ADR-0004** — frozen fixtures, four-axis benchmark methodology,
  reproducibility checklist.

### 6.2 Module layout (planned, not yet implemented)

```
src/pubmed_digest/
├── __init__.py           ← package marker, version
├── cli.py                ← entry point; argparse / typer
├── config.py             ← models.toml + runtime config loader
├── ncbi/
│   ├── client.py         ← rate-limited HTTP client (ESearch/ESummary/EFetch)
│   ├── cache.py          ← request-hash on-disk cache
│   └── models.py         ← Pydantic models for ESummary records
├── retrieval/
│   ├── ranker.py         ← deterministic hybrid ranker (ADR-0001)
│   └── pipeline.py       ← orchestration: query → top_k abstracts
├── llm/
│   ├── router.py         ← role-routed LiteLLM caller (ADR-0003)
│   ├── cache.py          ← SQLite-backed LLM call cache (ADR-0003)
│   ├── prompts/          ← versioned prompt templates
│   └── verifier.py       ← post-generation grounding verifier (ADR-0002)
├── digest/
│   ├── schema.py         ← PaperCard, Digest, Citation Pydantic models
│   ├── synthesize.py     ← per-card + cross-paper synthesis orchestration
│   └── export.py         ← Markdown / JSON exporters (pure functions)
└── logging.py            ← structured-log setup

tests/                    ← unit + golden-fixture tests
evals/                    ← benchmark harness, fixtures, results (ADR-0004)
docs/
├── SPEC.md
└── adr/0001-0005-*.md
```

### 6.3 External dependencies (planned)

- `httpx` — async NCBI client.
- `litellm` — provider-agnostic LLM caller.
- `instructor` — Pydantic-validated structured outputs.
- `pydantic` — schemas.
- `typer` (or stdlib `argparse`) — CLI.
- `tenacity` — retries with backoff.
- Standard dev tooling per the inherited Fabrica toolchain (ADR-0005).

---

## 7. Key decisions (load-bearing)

The four binding decisions are in `docs/adr/`:

1. [`0001-metadata-first-retrieval.md`](adr/0001-metadata-first-retrieval.md)
   — ESearch → ESummary → rank → EFetch(top_k); deterministic hybrid
   ranker over keyword/MeSH match, recency, pub-type, journal.
2. [`0002-structured-output-grounding.md`](adr/0002-structured-output-grounding.md)
   — Pydantic schemas via Instructor + LiteLLM; closed-set citation
   rule; post-generation grounding verifier; abstention as a
   first-class output.
3. [`0003-model-routing-policy.md`](adr/0003-model-routing-policy.md)
   — two roles (`card`, `synthesis`); `models.toml` pins exact IDs;
   primary/fallback per role; quality-or-cost-or-latency switching
   rule.
4. [`0004-reproducible-benchmark-methodology.md`](adr/0004-reproducible-benchmark-methodology.md)
   — frozen fixtures, four orthogonal scoring axes (retrieval,
   grounding, substantive, cost/latency), LLM-judge with committed
   rubric, dated reports.

ADR [`0005-toolchain.md`](adr/0005-toolchain.md) preserves the
inherited Fabrica toolchain rationale (uv, ruff, pyright, hatchling).

---

## 8. Production drill (Phase 1 minimum)

Per the curriculum's production-readiness rubric:

- [ ] **Dockerfile** for reproducible CLI execution (already
      present from Fabrica; will be extended with the runtime entry
      point).
- [ ] **Structured logs** with: query, esearch_count, summary_count,
      top_k, fetch_count, per-call latency, model, input/output
      tokens, USD cost, and a stable `run_id`.
- [ ] **Rate-limit + retry + cache layer** for NCBI calls
      (3 req/s without API key, 10 req/s with key; bounded
      exponential backoff with jitter; on-disk request-hash cache).
- [ ] **Failure-mode table** in the README covering: PubMed outage,
      empty result set, partial result set, NCBI 429, LLM provider
      outage, structured-output validation failure, grounding
      verification failure, budget exceeded, cache miss during eval
      (hard fail per ADR-0004).
- [ ] **Secrets handling** — NCBI API key and LLM provider keys via
      env vars; `.env.example` committed; never logged.

---

## 9. Quality bar (per `CURRICULUM.md`)

- [ ] README with: problem statement, target user, architecture,
      install/run, testing, non-goals — done in scaffold; will be
      expanded as features land.
- [ ] "Who this is for" + "Why it matters" sections — done.
- [ ] `pytest`, `pyright` (strict), `ruff`, green GitHub Actions CI —
      inherited from Fabrica; passing as of this commit.
- [ ] ADRs for non-trivial decisions — 0001–0004 land in this commit.
- [ ] Benchmark / evaluation section — wired in `evals/`, lands once
      the pipeline exists.
- [ ] Safety / limitations section — present in README; expands when
      the LLM is wired in.
- [ ] One primary proof asset beyond code — for this engineering-first
      repo: the dated benchmark report at `evals/results-YYYY-MM-DD.md`.

---

## 10. Out-of-scope guardrails

The following are explicit "do not build in v1" commitments:

- Web UI, REST API, or any networked service.
- A persistent application database. Local caches are allowed for NCBI
  responses and LLM call reuse, but they are implementation caches, not
  user-facing state.
- A vector index of any kind.
- Any patient-facing or clinical-decision feature.
- Multi-tenant features (auth, accounts, quotas).
- Auto-fetching or auto-updating fixtures during the eval.

If any of these are needed in a Phase 2 project, that is *that
project's* scope — not this one's.

---

## 11. Open questions (to resolve before implementation)

1. **CLI ergonomics.** Typer or argparse? Lean argparse for zero new
   deps unless typer's UX earns its keep on the sub-command surface.
2. **NCBI cache backend.** Plain filesystem (request hash → JSON file)
   vs SQLite. Filesystem is simpler; SQLite gives atomicity for
   concurrent runs. Likely filesystem for NCBI responses in v1. LLM call
   caching is separate and follows ADR-0003's SQLite-backed cache.
3. **API key management.** Document `NCBI_API_KEY` and provider keys
   via `.env.example` only? Or build a `--config` flag that points at
   a local TOML? Likely `.env` only for v1 — TOML config is for
   `models.toml`, not secrets.
4. **Markdown export structure.** Per-paper-card-then-synthesis vs
   synthesis-then-cards. Synthesis-first reads better for the user's
   question; cards-first reads better as a brief. Default to
   synthesis-first with a `--cards-first` flag if the eval shows users
   want it.

These do not block the design phase. They are flagged for
implementation-time decision.

---

## 12. Changelog

- **2026-05-01** — Initial design phase. SPEC and ADRs 0001–0004
  authored alongside the Fabrica → pubmed-digest scaffold rename. No
  app code yet.
