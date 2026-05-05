"""Offline benchmark-fixture inventory for pubmed-digest.

The first Phase 1 implementation slice does not make live PubMed or live LLM
calls yet. Instead, this module validates the frozen fixture scaffold and
writes a dated inventory report that future benchmark work can build on.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    # Keep the benchmark runnable from the repo root without requiring install-time path tweaks.
    sys.path.insert(0, str(PROJECT_SRC))

RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class FixtureInventoryRow:
    """One per-query fixture inventory record."""

    query_id: str
    expected_behavior: str
    tags: list[str]
    golden_status: str
    pubmed_response_files: int


def collect_fixture_inventory() -> list[FixtureInventoryRow]:
    """Load the scaffolded fixture set and summarize its current completeness."""
    from pubmed_digest.eval_fixtures import (
        count_pubmed_response_files,
        load_all_golden_cases,
        load_query_fixtures,
    )

    queries = load_query_fixtures()
    golden_cases = load_all_golden_cases()
    response_counts = count_pubmed_response_files()

    rows: list[FixtureInventoryRow] = []
    for query in queries:
        golden_case = golden_cases[query.id]
        rows.append(
            FixtureInventoryRow(
                query_id=query.id,
                expected_behavior=query.expected_behavior,
                tags=query.tags,
                golden_status=golden_case.status,
                pubmed_response_files=response_counts.get(query.id, 0),
            )
        )
    return rows


def write_results(rows: list[FixtureInventoryRow]) -> Path:
    """Write a date-stamped markdown report describing fixture readiness."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = RESULTS_DIR / f"results-{today}.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    scaffold_count = sum(1 for row in rows if row.golden_status == "scaffold")
    captured_count = sum(1 for row in rows if row.pubmed_response_files > 0)

    lines = [
        f"# Fixture inventory — {today}",
        "",
        f"- Queries defined: {len(rows)}",
        f"- Golden cases still in scaffold status: {scaffold_count}",
        f"- Queries with captured PubMed response files: {captured_count}",
        "",
        "| query_id | expected behavior | tags | golden status | captured response files |",
        "|----------|-------------------|------|---------------|-------------------------|",
    ]
    for row in rows:
        tags = ", ".join(row.tags)
        lines.append(
            f"| {row.query_id} | {row.expected_behavior} | {tags} | "
            f"{row.golden_status} | {row.pubmed_response_files} |"
        )

    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def main() -> None:
    """Collect the offline fixture inventory and persist a dated report."""
    rows = collect_fixture_inventory()
    out_path = write_results(rows)
    print(f"Wrote fixture inventory for {len(rows)} queries to {out_path}")


if __name__ == "__main__":
    main()
