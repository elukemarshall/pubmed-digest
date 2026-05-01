"""Benchmark template for projects created from this template.

Pattern: define a small set of evaluation cases, define one or more model
backends to test, run each (case, backend) pair, write results to a dated
markdown table. The default backend is a stub so the template runs with no
external dependencies; derived projects swap in real LiteLLM-backed calls.

See `evals/README.md` for the upgrade path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class Case:
    """One evaluation case — input prompt and expected behavior."""

    id: str
    prompt: str
    expected_keywords: list[str]


@dataclass
class Backend:
    """One backend under test — name plus a callable that returns a response."""

    name: str
    invoke: Callable[[str], str]


@dataclass
class Result:
    """One (case, backend) outcome captured during a benchmark run."""

    case_id: str
    backend: str
    response: str
    latency_ms: float
    matched_keywords: int


# --- Sample cases (replace with real evaluation set in derived projects) ---

CASES: list[Case] = [
    Case(
        id="biology_basic",
        prompt="In one sentence, what is the function of mitochondria?",
        expected_keywords=["energy", "ATP", "cell"],
    ),
    Case(
        id="biotech_methodology",
        prompt="In two sentences, what does CRISPR-Cas9 enable researchers to do?",
        expected_keywords=["gene", "edit", "DNA"],
    ),
]


# --- Sample backend (replace with real LiteLLM-backed calls) ---


def _stub_invoke(prompt: str) -> str:
    """Placeholder backend that echoes the prompt.

    Derived projects should replace this with real LLM calls. Example
    upgrade using LiteLLM (after `uv add litellm`):

        from litellm import completion

        def claude_sonnet(prompt: str) -> str:
            response = completion(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
    """
    return f"[stub response] Echo: {prompt[:80]}"


BACKENDS: list[Backend] = [
    Backend(name="stub", invoke=_stub_invoke),
]


def score(case: Case, response: str) -> int:
    """Count how many expected keywords appear in the response (case-insensitive)."""
    response_lower = response.lower()
    return sum(1 for kw in case.expected_keywords if kw.lower() in response_lower)


def run_benchmark() -> list[Result]:
    """Run every case against every backend and return the results."""
    results: list[Result] = []
    for case in CASES:
        for backend in BACKENDS:
            start = time.perf_counter()
            response = backend.invoke(case.prompt)
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(
                Result(
                    case_id=case.id,
                    backend=backend.name,
                    response=response,
                    latency_ms=latency_ms,
                    matched_keywords=score(case, response),
                )
            )
    return results


def write_results(results: list[Result]) -> Path:
    """Write results as a date-stamped markdown table; return the file path."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = RESULTS_DIR / f"results-{today}.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Benchmark results — {today}",
        "",
        "| case | backend | latency (ms) | matched keywords | response (truncated) |",
        "|------|---------|--------------|------------------|----------------------|",
    ]
    for r in results:
        truncated = r.response.replace("|", "\\|").replace("\n", " ")[:80]
        lines.append(
            f"| {r.case_id} | {r.backend} | {r.latency_ms:.1f} | "
            f"{r.matched_keywords} | {truncated} |"
        )
    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def main() -> None:
    """Run the benchmark and write a dated results file."""
    results = run_benchmark()
    out_path = write_results(results)
    print(f"Wrote {len(results)} results to {out_path}")


if __name__ == "__main__":
    main()
