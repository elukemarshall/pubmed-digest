"""Helpers for the frozen benchmark fixture scaffold."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

type NonEmptyString = Annotated[str, Field(min_length=1)]
type PMID = Annotated[str, Field(min_length=1, pattern=r"^\d+$")]
FixtureStatus = Literal["scaffold", "captured"]

DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "evals" / "fixtures"
DEFAULT_QUERY_FIXTURES_PATH = DEFAULT_FIXTURES_DIR / "queries.jsonl"
DEFAULT_GOLDEN_DIR = DEFAULT_FIXTURES_DIR / "golden"
DEFAULT_PUBMED_RESPONSES_DIR = DEFAULT_FIXTURES_DIR / "pubmed_responses"


class QueryFixture(BaseModel):
    """One benchmark query definition loaded from ``queries.jsonl``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: NonEmptyString
    query: NonEmptyString
    tags: list[NonEmptyString] = Field(min_length=1)
    expected_behavior: NonEmptyString
    notes: str | None = None


class GoldenCase(BaseModel):
    """Expected scoring targets for one benchmark query."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query_id: NonEmptyString
    status: FixtureStatus = "scaffold"
    relevant_pmids: list[PMID] = Field(default_factory=list)
    key_facts: list[NonEmptyString] = Field(default_factory=list)
    abstention_targets: list[NonEmptyString] = Field(default_factory=list)
    notes: str | None = None


def load_query_fixtures(path: Path | str = DEFAULT_QUERY_FIXTURES_PATH) -> list[QueryFixture]:
    """Load newline-delimited query fixtures from disk."""
    query_path = Path(path)
    fixtures: list[QueryFixture] = []
    with query_path.open() as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            fixtures.append(QueryFixture.model_validate(json.loads(stripped)))
    return fixtures


def load_golden_case(path: Path | str) -> GoldenCase:
    """Load one golden case JSON file."""
    golden_path = Path(path)
    with golden_path.open() as fh:
        return GoldenCase.model_validate(json.load(fh))


def load_all_golden_cases(
    directory: Path | str = DEFAULT_GOLDEN_DIR,
) -> dict[str, GoldenCase]:
    """Load all golden case files keyed by query ID."""
    golden_dir = Path(directory)
    return {
        golden_case.query_id: golden_case
        for golden_case in (load_golden_case(path) for path in sorted(golden_dir.glob("*.json")))
    }


def count_pubmed_response_files(
    directory: Path | str = DEFAULT_PUBMED_RESPONSES_DIR,
) -> dict[str, int]:
    """Count captured PubMed response JSON files for each query fixture directory."""
    pubmed_dir = Path(directory)
    counts: dict[str, int] = {}
    for path in sorted(pubmed_dir.iterdir()):
        if path.is_dir():
            counts[path.name] = sum(
                1 for response_file in path.rglob("*.json") if response_file.is_file()
            )
    return counts
