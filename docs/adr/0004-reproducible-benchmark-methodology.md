# ADR-0004: Reproducible Benchmark Dataset and Hybrid Scoring Methodology

**Status:** Accepted
**Date:** 2026-05-01
**Deciders:** Luke Marshall

## Context

Every LLM-using project must answer:

1. Which model(s) and why?
2. What alternatives were compared?
3. How was quality measured?
4. Latency and cost notes.
5. Known failure modes.

`pubmed-digest` cannot answer any of those credibly without a benchmark.
And the benchmark itself must be reproducible — running the same eval
on the same fixtures must yield the same numbers, regardless of who
runs it or when. That is the only way ADR-0003's "swap models on
measured deltas" rule has teeth.

Two specific reproducibility risks need explicit handling:

- **Live data drift:** PubMed indexes ~1M new records per year and
  rewrites old summaries on schema changes. A benchmark that hits live
  PubMed is non-reproducible by construction — the fixtures change
  underneath you.
- **LLM nondeterminism:** even at temperature 0, frontier models drift
  across versions and silently across minor provider updates. The
  benchmark must record exact model IDs, prompt-template versions,
  and dates so a re-run can detect drift rather than absorb it.

The benchmark is also the v1 evidence asset for the project — it is
the artifact a hiring manager actually reads. It needs to be honest,
small enough to finish, and big enough to defend a model choice.

## Decision

### Frozen fixtures

The benchmark runs against **frozen, committed fixtures** — never live
PubMed. Concretely:

- A directory `evals/fixtures/` contains:
  - `queries.jsonl` — N benchmark queries (target: N = 25 for v1).
  - `pubmed_responses/` — captured ESearch, ESummary, and EFetch
    responses for each query, keyed by request hash.
  - `golden/` — per-query expected outputs: relevant PMIDs, key facts
    that must appear, and abstention triggers (claims that should *not*
    appear because the abstracts do not support them).
- Fixtures are captured once via a `evals/capture.py` script that hits
  live PubMed, then committed. Re-capture is a deliberate, reviewed
  PR — never an automatic step in the eval.
- The NCBI client is wired so that during eval runs the cache layer
  returns the fixtures and never makes a network call. A network call
  during an eval run is a hard failure.

### Query set composition

The 25 v1 queries cover:

- 10 well-defined biomedical questions with strong PubMed coverage
  (e.g., specific drug + outcome).
- 5 queries with low-coverage / niche topics, to stress the small-N
  code path.
- 5 queries known to surface mixed-quality evidence (case reports,
  reviews, RCTs intermixed) to stress the metadata-aware ranker.
- 5 abstention queries: questions whose answer is plausibly *not*
  in any of the top-k retrieved abstracts. Used to grade whether the
  pipeline declines confabulation per ADR-0002.

The query set is not large enough for academic publication. It is
large enough to defend a model choice in an ADR.

### Hybrid scoring methodology

Each (query, model) pair is graded along **four orthogonal axes**:

1. **Retrieval quality** — does the metadata-first ranker (ADR-0001)
   surface the relevant PMIDs?
   - `recall@k` — fraction of golden-relevant PMIDs in top-k.
   - `precision@k` — fraction of top-k that are golden-relevant.
   - These are pure functions of the ranker; the LLM is not in the
     loop. They depend only on `card`/`synthesis` model choice when a
     future iteration adds embedding rerank.

2. **Grounding fidelity** — does the synthesis honor ADR-0002's rules?
   - **Citation coverage:** % of synthesis sentences with ≥1 inline
     PMID citation.
   - **Closed-set correctness:** % of cited PMIDs that appear in the
     run's retrieved set (must be 100%; deviations are flagged).
   - **Metadata equality:** % of card metadata fields that match
     ESummary verbatim (must be 100%).

3. **Substantive correctness** — does the synthesis actually contain
   the key facts the abstracts contain, and abstain on facts they
   don't?
   - **Key-fact recall:** % of golden key facts present in the
     synthesis. Graded by an LLM-judge over the structured `Digest`
     using a separate, high-tier model from a different provider than
     the one being benchmarked, with the prompt and rubric committed
     in `evals/judge_prompt.md`.
   - **Abstention rate on negatives:** % of abstention queries where
     the synthesis correctly declined or routed the unsupported claim
     into `Digest.abstentions`.
   - LLM-judge calls are themselves cached so re-runs are cheap and
     deterministic given the same Digest input.

4. **Cost and latency** — measured directly from LiteLLM call logs.
   - p50 / p95 wall-clock latency per query.
   - USD per query (broken down by `card` vs `synthesis` per ADR-0003).
   - Total benchmark cost per model.

### Scoring composition

A single composite score is **not** computed. Each model gets a
four-axis result line that the ADR-0003 switching rule reads. Composite
scores hide the tradeoffs this project needs to make visible
(quality vs cost vs latency).

### Outputs

After every benchmark run:

- `evals/results-YYYY-MM-DD.md` — committed Markdown report with the
  per-model table, exact model IDs, dates, prompt-template version
  hashes, and observed total cost.
- `evals/results-YYYY-MM-DD.jsonl` — committed raw per-query records
  (model, query_id, scores, latency, cost) for any future re-analysis.
- `evals/results-latest.md` — a symlink/pointer to the most recent
  report; the README links to this rather than to a dated file.

### Re-running policy

- **On every model swap:** mandatory benchmark run, results committed,
  ADR-0003 addendum referencing the new dated report.
- **Quarterly:** re-run with current frontier IDs even if no swap is
  pending, to catch silent drift.
- **On prompt-template change:** re-run; invalidate caches; commit.

### Reproducibility checklist

A run is considered reproducible only if all of the following hold:

- All fixtures hash-match the committed copies.
- `models.toml` is committed.
- Prompt templates' content hashes are recorded in the report.
- The judge model ID and judge prompt are recorded.
- The cache directory was empty (or only contained committed fixture
  responses) at run start, recorded in the report header.
- Random seeds (where the LLM accepts them) are recorded.

## Options Considered

### Option A — Live PubMed, no fixtures

Run the benchmark against current PubMed every time.

- **Pro:** simplest setup; no fixture-capture scripts.
- **Con:** non-reproducible by construction. Two runs a week apart
  will disagree, and there is no way to tell whether a regression is
  the model or the data.
- **Con:** burns NCBI quota.
- **Con:** any future hiring-manager-style review cannot rerun the
  benchmark — fail.

### Option B — Live LLM, fixtures only for retrieval

Freeze PubMed but call models live and grade with LLM-judge live.

- **Pro:** retrieval is deterministic.
- **Con:** model nondeterminism still drifts results; can't isolate
  prompt vs model regressions.
- **Con:** cost per run scales with model count.

### Option C — Frozen fixtures + LLM-judge with a committed rubric (chosen)

Both retrieval inputs and grading are reproducible; only the model
under test is "live," and its calls are cached so subsequent re-runs
are free.

- **Pro:** deterministic *given the same model versions*.
- **Pro:** model-version drift becomes visible — that is the *point*.
- **Pro:** judge-model caching means a re-run on the same Digest
  outputs is free.
- **Con:** fixture maintenance is real work. Mitigated by capping
  query count at 25 for v1.

### Option D — Use only an existing biomedical benchmark (PubMedQA, BioASQ)

- **Pro:** authoritative; published baselines exist.
- **Con:** PubMedQA/BioASQ test QA, not the metadata-first
  retrieval+digest workflow this CLI implements. Wrong unit.
- **Pro (deferred):** Phase 2's `biomedical-research-agent` is the
  right place to evaluate against PubMedQA. Reference future use, do
  not adopt for v1.

## Trade-off Analysis

The biggest tradeoff is **fixture maintenance vs reproducibility**.
Fixtures need to be re-captured periodically when PubMed schemas
evolve or queries become uninteresting (no more recent literature).
We accept this maintenance cost because the alternative — non-reproducible
benchmarks — destroys the entire point of the exercise.

LLM-judge is the second tradeoff: it introduces a meta-LLM dependency
and its own cost. We mitigate by:

1. Using a different, higher-tier model than any model under test, to
   avoid in-family bias.
2. Committing the rubric prompt verbatim and version-hashing it.
3. Caching judge outputs by Digest hash so the marginal cost of a
   re-run after fixing a prompt template is the new model's calls
   only.

## Consequences

**Easier:**

- "Why this model?" is answered with a committed dated report, not a
  tweet-thread vibe.
- Regression detection is real: re-running v0 fixtures on v1 prompts
  shows whether prompt edits helped or hurt.
- The eval doubles as the project's primary evidence asset per
  Phase 1's quality bar.

**Harder:**

- Initial fixture capture is a one-time cost (a few hours).
- Every model swap costs an eval run (~$1–$3 expected for 25 queries
  per model).
- LLM-judge bias is real and cannot be fully eliminated; we partially
  mitigate it but the report must say so explicitly in its limitations
  section.

**To revisit:**

- After v1 ships: if the 25-query set is too small to discriminate
  between candidate models on real differences, expand to 50–100.
- If a Phase 2 project (`biomedical-research-agent`) reuses this
  benchmark harness, factor it out of `evals/` into a small library
  rather than copying.
- If LLM-judge bias materially distorts conclusions, consider human
  spot-grading on a 5-question subset as a second signal.

## Action Items

1. [ ] Build `evals/capture.py` for one-time fixture capture.
2. [ ] Hand-author `evals/fixtures/queries.jsonl` and the matching
       `evals/fixtures/golden/` rubrics.
3. [ ] Implement the four-axis grader (retrieval, grounding,
       substantive, cost/latency) with deterministic scoring where
       possible and an explicit LLM-judge stage where not.
4. [ ] Wire the harness to the role-routed caller from ADR-0003.
5. [ ] Commit the v1 report at `evals/results-YYYY-MM-DD.md` and
       update the README to link `evals/results-latest.md`.
