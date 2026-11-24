"""Edge-case tests for the benchmark fixture loaders."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from pubmed_digest.eval_fixtures import (
    count_pubmed_response_files,
    load_all_golden_cases,
    load_golden_case,
    load_query_fixtures,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_load_query_fixtures_skips_blank_lines(tmp_path: Path) -> None:
    """Blank and whitespace-only lines in queries.jsonl are ignored."""
    record = {"id": "q1", "query": "statins", "tags": ["cv"], "expected_behavior": "answer"}
    path = tmp_path / "queries.jsonl"
    path.write_text(f"\n{json.dumps(record)}\n   \n")

    fixtures = load_query_fixtures(path)

    assert [fixture.id for fixture in fixtures] == ["q1"]


def test_query_fixture_rejects_unknown_fields(tmp_path: Path) -> None:
    """Unexpected keys fail loudly instead of being silently dropped."""
    record = {
        "id": "q1",
        "query": "statins",
        "tags": ["cv"],
        "expected_behavior": "answer",
        "surprise": True,
    }
    path = tmp_path / "queries.jsonl"
    path.write_text(json.dumps(record))

    with pytest.raises(ValidationError):
        load_query_fixtures(path)


def test_golden_case_rejects_non_numeric_pmid(tmp_path: Path) -> None:
    """PMIDs must be digit-only strings."""
    path = tmp_path / "q1.json"
    path.write_text(json.dumps({"query_id": "q1", "relevant_pmids": ["PMID123"]}))

    with pytest.raises(ValidationError):
        load_golden_case(path)


def test_count_pubmed_response_files_ignores_stray_files(tmp_path: Path) -> None:
    """Only per-query directories are counted, recursing into nested JSON files."""
    (tmp_path / "q1" / "esearch").mkdir(parents=True)
    (tmp_path / "q1" / "esearch" / "page1.json").write_text("{}")
    (tmp_path / "q1" / "notes.txt").write_text("not json")
    (tmp_path / "q2").mkdir()
    (tmp_path / "README.json").write_text("{}")

    assert count_pubmed_response_files(tmp_path) == {"q1": 1, "q2": 0}


def test_load_all_golden_cases_keys_by_query_id_and_skips_non_json(tmp_path: Path) -> None:
    """Golden cases are keyed by their declared query_id, not the file name."""
    (tmp_path / "a.json").write_text(json.dumps({"query_id": "q-alpha"}))
    (tmp_path / "b.json").write_text(json.dumps({"query_id": "q-beta", "status": "captured"}))
    (tmp_path / "notes.md").write_text("ignored")

    cases = load_all_golden_cases(tmp_path)

    assert sorted(cases) == ["q-alpha", "q-beta"]
    assert cases["q-alpha"].status == "scaffold"
    assert cases["q-beta"].status == "captured"


def test_golden_case_rejects_unknown_status(tmp_path: Path) -> None:
    """Status is a closed set so typos cannot masquerade as captured fixtures."""
    path = tmp_path / "q1.json"
    path.write_text(json.dumps({"query_id": "q1", "status": "done"}))

    with pytest.raises(ValidationError):
        load_golden_case(path)
