# ADR-0001: Metadata-First Retrieval Pipeline

**Status:** Accepted
**Date:** 2026-05-01
**Deciders:** Luke Marshall

## Context

`pubmed-digest` answers a single user question by surfacing and
summarizing relevant biomedical literature from PubMed. The naive
implementation of "get me the top papers on X" is to call PubMed
ESearch, fetch every matching abstract, and feed all of them into an
LLM. That breaks immediately on any real biomedical query:

- A query like "GLP-1 agonist cardiovascular outcomes" returns tens of
  thousands of PubMed records.
- ESearch returns PMIDs only — no titles, no abstracts. Naive pipelines
  call EFetch on every PMID, paying NCBI's rate-limit and bandwidth cost
  for thousands of full abstracts the user will never see.
- Abstracts are large; pushing 10K+ of them into an LLM context is both
  expensive and lossy. Even with Gemini-tier long context, signal drowns
  in noise.
- Recency, journal source, and study type matter to biomedical readers
  in ways pure semantic similarity does not capture. A 2026 RCT in NEJM
  is not interchangeable with a 2014 case report.

PaperQA2's design point (current scientific RAG state of the art) is
explicit on this: scientific retrieval needs metadata-aware ranking
*before* full-text retrieval, not embedding similarity over a giant
chunk store as the first move. We adopt the same design principle,
narrowed for v1's abstract-only scope.

## Decision

Adopt a **metadata-first retrieval pipeline** with strict ordering:

```
ESearch(query) -> PMIDs (capped, e.g. 200)
   |
   v
ESummary(PMIDs) -> lightweight metadata records
   (title, journal, pub date, pub types, authors, MeSH headings)
   |
   v
Score & rank using hybrid signals:
   - keyword/BM25-style match on title + MeSH
   - recency decay (half-life configurable; default ~5 years)
   - publication-type weighting (RCT, meta-analysis, review > case report)
   - journal-quality signal (allowlist or impact tier; configurable)
   |
   v
EFetch(top_k PMIDs)  -> full abstracts only for the ranked top-k
   |
   v
Per-paper structured summary  +  cross-paper digest synthesis
```

**Caps and defaults:**

- `esearch_retmax = 200` (configurable, hard cap 1000)
- `top_k = 10` for abstract retrieval (configurable, hard cap 25)
- ranker is deterministic and pure given the same metadata + config

**Rate-limit + caching contract:**

- All NCBI calls go through a rate-limited client (3 req/s without API
  key, 10 req/s with key — values pinned in a `models.toml`-equivalent
  config alongside the model IDs).
- ESearch, ESummary, and EFetch responses are cached on disk by request
  hash; cache invalidation is explicit (`--no-cache` flag) and TTL is
  configurable.
- Failures (network, 429, 5xx) use bounded exponential backoff with
  jitter; after retry exhaustion the CLI fails loud with a clear
  message rather than degrading silently.

**Out of scope for v1:**

- Embedding-based retrieval over abstracts. Deferred to a future
  iteration if the metadata-only ranker proves insufficient on the
  evaluation set (see ADR-0004).
- Full-text PMC retrieval. Abstract-only is the v1 grounding surface.
- Cross-source enrichment (Europe PMC, Semantic Scholar). Optional
  enrichment hooks may be added but PubMed is the source of truth.

## Options Considered

### Option A — Naive "fetch everything, embed, retrieve" pipeline

ESearch -> EFetch all -> chunk + embed -> vector retrieval -> LLM.

- **Pro:** conceptually simple; matches generic RAG tutorials.
- **Con:** wastes NCBI quota on abstracts that never reach the user.
- **Con:** loses metadata signal (recency, study type, journal) that
  biomedical readers actually care about.
- **Con:** an irrelevant abstract embedded close to a relevant one in
  vector space ranks above a more relevant abstract that happens to
  use different terminology.
- **Con:** expensive at any non-toy query volume.

### Option B — Pure semantic search over a pre-built abstract index

Maintain a local FAISS/Chroma index of abstracts; query by embedding
similarity only.

- **Pro:** fast at query time.
- **Con:** index staleness — PubMed indexes ~1M new records per year.
- **Con:** still loses metadata signal.
- **Con:** turns the project into a vector-DB ops project, which is not
  what Phase 1 is teaching.

### Option C — Metadata-first hybrid (chosen)

Two-stage: cheap metadata pass narrows the candidate set, expensive
abstract pass is bounded and ranked.

- **Pro:** matches the actual structure of the NCBI APIs (ESearch +
  ESummary are designed exactly for this) instead of fighting it.
- **Pro:** uses metadata signal that pure embedding retrieval discards.
- **Pro:** bounded cost — k abstracts fetched, k abstracts summarized,
  predictable LLM spend.
- **Pro:** legible to the user — they can see *why* a paper was ranked
  high (e.g., "RCT, 2025, NEJM, MeSH match: GLP-1") without inspecting
  embeddings.
- **Con:** keyword/MeSH ranking can miss semantically-relevant papers
  that use different terminology. Acceptable for v1 with the door open
  to an embedding-augmented variant in a later iteration once the
  benchmark in ADR-0004 quantifies the gap.

## Trade-off Analysis

The biggest tradeoff is **recall vs cost**: pure semantic search may
surface papers a metadata-first ranker misses. We accept this tradeoff
because:

1. The benchmark methodology in ADR-0004 will measure the gap
   quantitatively rather than asserting it.
2. Recall problems are recoverable in a later iteration by adding an
   embedding stage *between* ESummary and the top-k cut. They are not
   recoverable in a pure-semantic system that has already discarded
   metadata signal.
3. Phase 1's teaching goal is "polished biotech tooling that ships" —
   not "production vector retrieval." A metadata-first pipeline is the
   right shape to learn the API, rate-limit, and structured-output
   skills that Phase 1 targets.

## Consequences

**Easier:**

- Cost is predictable and small (k abstracts, k LLM calls per digest).
- Failure modes map cleanly to the API stages: ESearch failure ≠
  ESummary failure ≠ EFetch failure ≠ LLM failure. Each gets its own
  retry / fallback / fail-loud rule.
- The ranker is a pure function of metadata + config and is trivially
  unit-testable with frozen fixtures.

**Harder:**

- Designing the hybrid score weights well takes careful eval work
  (see ADR-0004). Magic numbers in the ranker are an obvious smell;
  the benchmark must show the weights earn their place.
- Edge case: queries with very few PubMed hits (<10) need a different
  code path that skips ranking and digests whatever is there.

**To revisit:**

- After ADR-0004's first benchmark run: if recall is meaningfully below
  a sensible baseline, add an embedding stage between ESummary and
  top-k and benchmark again.
- If a downstream Phase 2 project (e.g., `biomedical-research-agent`)
  needs full-text PMC retrieval, factor the retrieval client out of
  pubmed-digest into a shared library rather than scope-creeping this
  CLI.

## Action Items

1. [ ] Implement the rate-limited NCBI client (ESearch, ESummary,
       EFetch) with caching and backoff.
2. [ ] Implement the deterministic hybrid ranker.
3. [ ] Wire structured logging at each stage: query, esearch_count,
       summary_count, fetch_count, latency, cost.
4. [ ] Document the failure-mode table in the README.
