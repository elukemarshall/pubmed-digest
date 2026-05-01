# Benchmarks (`evals/`)

The reusable evaluation pattern for projects created from this template.

## Why this exists

The curriculum's quality bar requires every LLM- or ML-backed project to answer:

1. Which model(s) and why?
2. What alternatives were compared?
3. How was quality measured?
4. What is the latency / cost profile?
5. What are the known failure modes?

This `evals/` directory is the reusable infrastructure for answering those questions reproducibly. It produces dated markdown tables you commit to git so quality trends become reviewable history.

## Pattern

- **`CASES`** — a small set of evaluation inputs with explicit expected behavior. Start with 5–30 cases. Quality > quantity.
- **`BACKENDS`** — one or more model configurations to test. The template ships with a stub backend that echoes input; derived projects replace it with real LiteLLM-backed calls.
- **`run_benchmark()`** — runs every case against every backend, captures latency, returns `Result` objects.
- **`write_results()`** — writes a dated markdown table to `results/results-YYYY-MM-DD.md`.

## Running

```bash
uv run python -m evals.benchmark
```

Output goes to `evals/results/results-YYYY-MM-DD.md`. Commit results only
when the cases and scoring rubric represent meaningful task evaluation. For
the stub output shape, see `evals/examples/stub-results.md`.

## Upgrading for real LLM evaluation

1. Add LiteLLM (and Instructor for structured outputs):

```bash
uv add litellm instructor
```

2. Replace the stub backend in `benchmark.py` with real calls:

```python
from litellm import completion

def claude_sonnet(prompt: str) -> str:
    response = completion(
        model="claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
```

3. Define `CASES` for your project's actual evaluation set (e.g., 30 PubMed queries with known good summaries for `pubmed-digest`).

4. Replace keyword-matching `score()` with something that fits the task: rubric-based grading, embedding similarity, structured-output validation, or LLM-as-judge.

## What this is not

- **Not a full evaluation framework.** For complex evals consider [Inspect](https://inspect.aisi.org.uk/), [LangSmith](https://smith.langchain.com/), or [Promptfoo](https://www.promptfoo.dev/).
- **Not academic benchmarking.** This is the "did my changes regress quality?" sanity check, run on every meaningful update.
- **Not a substitute for thoughtful test cases.** What you choose to measure determines what you can claim.
