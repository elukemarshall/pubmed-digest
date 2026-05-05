"""Tests for frozen benchmark fixture scaffolding."""

from __future__ import annotations

from pubmed_digest.eval_fixtures import (
    count_pubmed_response_files,
    load_all_golden_cases,
    load_query_fixtures,
)


def test_query_and_golden_fixture_ids_match() -> None:
    """Each scaffolded query should have exactly one golden-case file."""
    query_ids = {fixture.id for fixture in load_query_fixtures()}
    golden_ids = set(load_all_golden_cases())

    assert query_ids == golden_ids


def test_pubmed_response_directories_exist_for_each_query() -> None:
    """Each query scaffold should already have a reserved response directory."""
    query_ids = {fixture.id for fixture in load_query_fixtures()}
    response_counts = count_pubmed_response_files()

    assert set(response_counts) == query_ids
    assert all(count == 0 for count in response_counts.values())
