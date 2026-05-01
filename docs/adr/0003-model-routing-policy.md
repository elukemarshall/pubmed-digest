# ADR-0003: Backend Abstraction and Model Routing Policy

**Status:** Accepted
**Date:** 2026-05-01
**Deciders:** Luke Marshall

## Context

`pubmed-digest` calls an LLM in two distinct roles:

1. **Per-paper card** — short, factual extraction over a single
   abstract. Bulk: one call per top-k paper. Latency-sensitive only in
   aggregate; cost-sensitive per call.
2. **Cross-paper synthesis** — one reasoning-heavier call that ties
   the cards together into a digest answering the query. Quality
   matters more than cost on this single call.

This project treats model choice as a design decision, not a default.
Every LLM-using feature must answer: **which models, why, at what
cost, with what fallback?** And the implementation must keep the
answer swappable because the frontier moves every quarter.

This ADR pins **roles** and the policy for choosing models within those
roles. **Exact model IDs are pinned in `models.toml`** (or equivalent
config) at the moment of build, after a current-source verification
against provider docs. The ADR does not hard-code IDs that will rot.

## Decision

### Provider abstraction

Use **LiteLLM** as the single LLM caller everywhere. All calls are
made through `litellm.acompletion(model=<id-string>, ...)` wrapped by
**Instructor** (per ADR-0002) for structured outputs. No direct
provider SDKs are imported in app code.

This means swapping models is a config change, not a code change.

### Role catalog

Define two named roles in `models.toml`:

| Role | Purpose | Volume | Quality bar | Cost sensitivity |
|------|---------|--------|-------------|------------------|
| `card` | per-paper structured extraction | high (k per query) | medium — must follow schema and stay grounded | high — pays per top-k |
| `synthesis` | cross-paper digest | low (1 per query) | high — reasoning + citation discipline | low |

Each role has:

- a **primary** model ID,
- a **fallback** model ID (different provider where possible),
- a **date verified** field,
- intended-use notes,
- a per-run budget cap (USD).

### Routing rule (default tiers)

Stated as **capability tiers** rather than IDs, so this ADR survives
quarterly model churn. Exact IDs live in `models.toml`.

- **`card` role primary:** a current cheap+fast frontier or open-weight
  tier suited to cheap bulk summarization (e.g., a current Kimi K2.x
  frontier via OpenRouter, a current Gemini Flash tier, or a current
  Claude Haiku tier).
- **`card` role fallback:** a different-provider model in the same tier,
  to survive a single-provider outage without a manual config change.
- **`synthesis` role primary:** a current balanced reasoning frontier
  tier suited to structured extraction with strong reasoning, e.g., a
  current Claude Sonnet tier.
- **`synthesis` role fallback:** a current OpenAI flagship or Gemini Pro
  tier.

The primary/fallback choice is then committed to `models.toml` after
provider-doc verification at the moment the project is implemented.

### Switching rule

Models swap based on **measured benchmark deltas**, not vibes. The
benchmark in ADR-0004 reports per-role quality, latency, and cost
across at least three providers. A primary model is replaced when
the benchmark shows a meaningful improvement (≥10% on the relevant
quality metric, or ≥30% cost reduction at equal quality, or strictly
better latency at equal quality and cost).

Replacements are recorded in `evals/results-YYYY-MM-DD.md` and the
`models.toml` change carries a one-line rationale linking the eval.

### Budget guardrails

- A per-run budget (default `$0.50`) is enforced in code via LiteLLM's
  cost tracker. Exceeding it fails the run loud.
- A per-eval budget (default `$5`) gates benchmark execution; the
  harness aborts if a model would push the run past the cap.
- Both budgets are configurable in `models.toml`.

### Caching

Identical (model, prompt, temperature, schema) tuples are cached on
disk to a SQLite-backed key-value store. Cache hits cost zero. The
cache is keyed on a stable hash that includes the model ID and
prompt-template version so that swapping a model or editing a prompt
correctly invalidates.

### What lives in `models.toml`

```toml
# Verified IDs and tiers are filled in at implementation time after
# checking provider docs. This file is the source of truth; the ADR
# is the policy.

[card]
primary  = { provider = "...", model = "...", date_verified = "YYYY-MM-DD" }
fallback = { provider = "...", model = "...", date_verified = "YYYY-MM-DD" }
budget_per_card_usd = 0.005

[synthesis]
primary  = { provider = "...", model = "...", date_verified = "YYYY-MM-DD" }
fallback = { provider = "...", model = "...", date_verified = "YYYY-MM-DD" }
budget_per_run_usd = 0.10

[budgets]
per_run_usd  = 0.50
per_eval_usd = 5.00
```

## Options Considered

### Option A — Hard-code one provider's SDK

Pick Anthropic (or OpenAI), use their SDK directly.

- **Pro:** simplest. Best-in-class type hints.
- **Con:** violates the project's provider-agnostic routing policy.
- **Con:** swapping for a benchmark requires rewriting call sites.
- **Con:** a Claude-only portfolio reads as "pragmatic user" not
  "engineer who thinks about tradeoffs." This is a portfolio project.

### Option B — Single role, one model for everything

Use the same model for both per-paper cards and synthesis.

- **Pro:** simpler config.
- **Con:** wastes money on bulk extraction when a cheaper tier
  matches quality at a fraction of cost.
- **Con:** bottlenecks both calls behind the same provider's outages.
- **Con:** loses the legible "cheap bulk + smart synthesis" pattern
  that hiring managers look for.

### Option C — LiteLLM + Instructor + role-based routing (chosen)

Two roles, named in config, swap per-role independently.

- **Pro:** matches the actual cost/quality shape of the work.
- **Pro:** swap a provider in one line; survives a quarter of frontier
  movement without a code change.
- **Pro:** `card` and `synthesis` failures are independently
  recoverable.
- **Con:** adds a small `models.toml` and a routing helper. Worth it.

## Trade-off Analysis

The tradeoff is **abstraction overhead vs lock-in cost**. LiteLLM adds
a thin layer between us and provider SDKs; in exchange, we never write
a "migrate from X to Y" PR. For a project that explicitly tracks the
frontier quarterly, this is unambiguously the right tradeoff.

A subtler tradeoff: per-role routing means a future feature
(e.g., "add a reranker model") becomes a new role rather than a
refactor of an existing one. We accept this as good — roles are the
right unit of swap-ability.

## Consequences

**Easier:**

- Quarterly model refresh is a `models.toml` edit + benchmark run +
  ADR addendum, not a code rewrite.
- Per-role cost tracking falls out of LiteLLM's cost tracker for free.
- Failure isolation: a `card` provider outage does not take down
  synthesis (and vice versa).

**Harder:**

- Two roles means two prompt templates to maintain and two prompt
  versions to invalidate caches on. The cache key already accounts
  for this; the discipline is purely operational.
- Provider-specific quirks (Anthropic's tool-use schema, OpenAI's
  JSON mode) are abstracted by LiteLLM but occasionally leak. Where
  they leak, they get an ADR addendum, not a hand-rolled adapter.

**To revisit:**

- After ADR-0004's first benchmark run: confirm the role split earns
  its complexity. If `card` and `synthesis` end up using the same
  model anyway, collapse to one role.
- Quarterly: re-verify model IDs in `models.toml` against provider
  docs. Stale IDs are a real failure mode the curriculum is calling
  out — don't let this project become an example of it.
- If LiteLLM stops being the de-facto provider-agnostic layer (e.g.,
  if Pydantic AI's provider abstraction matures past it), revisit.

## Action Items

1. [ ] Create `models.toml` template with placeholder IDs and the
       date-verified field marked TODO.
2. [ ] At implementation time: verify current model IDs against
       provider docs, fill in `models.toml`, commit with the
       verification date in the commit message.
3. [ ] Implement the role-routed LLM caller (one helper that takes a
       role name and returns a configured Instructor client).
4. [ ] Wire LiteLLM cost tracking into structured logs with role,
       model, input/output tokens, latency, and USD per call.
