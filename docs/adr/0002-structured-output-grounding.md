# ADR-0002: Structured Output Contract and Grounding Rules

**Status:** Accepted
**Date:** 2026-05-01
**Deciders:** Luke Marshall

## Context

`pubmed-digest` produces two artifact types per run:

1. **Per-paper cards** — one structured record per top-k paper.
2. **Cross-paper digest** — one synthesized summary spanning all
   per-paper cards, used to answer the original query.

In any biomedical context, the cost of an unsupported claim is high.
Hallucinated mechanisms, fabricated trial outcomes, or made-up authors
are not just embarrassing — they make the tool unusable for its target
user (research and BD analysts who would otherwise verify by reading the
abstracts themselves).

Two failure modes specifically must be designed against:

- **Structural failure:** the model returns invalid JSON, missing
  fields, or wrong types. A downstream Markdown/JSON exporter must
  not have to defensively handle this; the boundary is the LLM call.
- **Grounding failure:** the model returns valid JSON whose claims are
  not supported by the abstracts retrieved for that run. This is the
  more dangerous failure because the output looks correct.

Both failure modes need first-class handling, not best-effort prompting.

## Decision

### Structured output enforcement

Use **Instructor** (`pip install instructor`) over **LiteLLM** to wrap
every LLM call. Output schemas are Pydantic models. The Instructor +
LiteLLM combination is the curriculum default per `MULTI_MODEL_STRATEGY.md`
because it is provider-agnostic and gives Pydantic-validated outputs
with built-in retry on schema violation.

Two top-level Pydantic schemas:

```python
class PaperCard(BaseModel):
    pmid: str                     # must equal the source PMID
    title: str                    # must equal ESummary title verbatim
    authors: list[str]            # from ESummary; not invented
    journal: str
    pub_date: str                 # ISO 8601 (YYYY or YYYY-MM-DD)
    pub_types: list[str]          # from ESummary
    tldr: str                     # <= 280 chars; abstract-grounded
    why_it_matters: str           # <= 500 chars; abstract-grounded
    key_findings: list[str]       # bullets; each abstract-grounded
    limitations: list[str]        # bullets; abstract-grounded or empty

class Digest(BaseModel):
    query: str
    paper_cards: list[PaperCard]
    cross_paper_synthesis: str    # answers the query using cards
    citations: list[Citation]     # see grounding rules below
    abstentions: list[str]        # claims the model declined to make
```

### Grounding rules (binding on the synthesis prompt and verified post-call)

1. **Citation-first**: every assertion in `cross_paper_synthesis` must
   carry an inline citation in the form `[PMID:12345678]`. Output is
   re-scanned post-generation; any sentence without at least one
   citation is flagged and either retried (≤2x) or rendered with an
   "uncited claim" warning marker. We do not strip uncited claims
   silently — the user must see the failure.
2. **Closed-set citations**: every PMID cited must appear in the
   `paper_cards` list for that run. Citations to PMIDs outside the
   retrieved set are a hard failure and trigger a retry.
3. **No invented metadata**: `title`, `authors`, `journal`, `pub_date`,
   `pub_types` must equal the corresponding ESummary fields verbatim.
   Verified by exact string comparison against the cached ESummary
   record post-generation. Mismatch triggers retry.
4. **Abstention is a first-class output**: when the abstracts do not
   contain enough information to answer part of the query, the model
   must populate `abstentions` rather than synthesize. We measure
   abstention behavior in the eval (ADR-0004); silent confabulation is
   the failure mode we are most explicitly designing against.
5. **No external knowledge in synthesis**: the model is prompted that
   `cross_paper_synthesis` may use only information present in the
   retrieved abstracts. Prior knowledge from training is explicitly
   disallowed even when correct, because it cannot be cited.

### Retry policy

- On structural failure (Pydantic validation error): Instructor retries
  up to 2x with the validation error appended.
- On grounding failure (post-validation citation/metadata check fails):
  one retry with a structured "the following claims were uncited /
  the following metadata diverged" feedback message.
- After retries are exhausted, the CLI emits a partial result with
  explicit warning markers and a non-zero exit code if `--strict` is
  set.

### Output formats

The structured `Digest` is the canonical artifact. Markdown and JSON
exporters are pure functions over `Digest`; they never call an LLM and
add no information.

## Options Considered

### Option A — Free-form Markdown output, post-hoc parsing

Ask the LLM for Markdown; parse fields with regex.

- **Pro:** simplest prompt.
- **Con:** every output format change breaks the parser.
- **Con:** silently ungrounded — there is no schema-level place to
  enforce citations or metadata fidelity.
- **Con:** tests devolve into regex tests over LLM-of-the-week.

### Option B — JSON mode without Pydantic validation

Provider-native JSON mode (OpenAI, Anthropic) with manual `json.loads`.

- **Pro:** fewer dependencies.
- **Con:** no schema enforcement beyond "is it parseable JSON". Missing
  fields, wrong types, extra fields are all tolerated by `json.loads`.
- **Con:** every consumer downstream re-validates defensively. The
  boundary leaks.

### Option C — Pydantic + Instructor + LiteLLM (chosen)

Schema is the contract; Instructor enforces it; LiteLLM keeps the
provider swappable per ADR-0003.

- **Pro:** one boundary, validated once, never again.
- **Pro:** retries on schema failure are automatic and bounded.
- **Pro:** swapping models requires zero downstream changes.
- **Con:** adds two dependencies. Acceptable; both are stable.
- **Con:** Instructor's retry logic costs tokens. Bounded by retry cap.

## Trade-off Analysis

The grounding rules add post-generation verification cost (a few string
comparisons and a citation scan). In return, we get a hard contract
between the LLM and the rest of the pipeline that is testable on frozen
fixtures without spending API credits.

The "fail loud, do not strip silently" rule for uncited claims is a
deliberate UX choice. A digest that quietly omits 30% of the model's
output is worse than one that shows the user "these 3 sentences had no
citation" — the user can decide what to do; the silent version pretends
nothing happened.

## Consequences

**Easier:**

- Downstream Markdown/JSON exporters become trivial pure functions.
- Eval grading (ADR-0004) operates over a typed object, not over
  free text.
- Citation completeness, metadata fidelity, and abstention rate become
  measurable per-run metrics, not vibes.

**Harder:**

- Prompt engineering must explicitly enforce the citation-first rule
  and survive the more aggressive retry path. Some models will need a
  few iterations of prompt tuning to hit a high first-try success
  rate.
- Authors-list verbatim equality is brittle when ESummary returns
  truncated authors ("Smith J, et al."). The verification rule treats
  trailing "et al." as canonical and matches the prefix.

**To revisit:**

- After the first benchmark run (ADR-0004): if a model has a
  consistently high grounding-failure rate after retries, route it
  to a different role in ADR-0003 rather than band-aiding the prompt.
- If a future iteration adds full-text PMC retrieval, the grounding
  surface widens and `Citation` may need section/paragraph anchors.

## Action Items

1. [ ] Implement `PaperCard`, `Digest`, and `Citation` Pydantic models.
2. [ ] Implement the post-generation grounding verifier (citation
       coverage, closed-set check, metadata equality).
3. [ ] Author the synthesis prompt template with the grounding rules
       baked in.
4. [ ] Add unit tests for the verifier using frozen fake-LLM outputs.
