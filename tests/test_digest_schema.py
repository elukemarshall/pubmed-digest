"""Tests for structured digest-domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pubmed_digest.digest.schema import Citation, Digest, PaperCard


def make_paper_card() -> PaperCard:
    """Create a representative paper card for schema tests."""
    return PaperCard(
        pmid="12345678",
        title="GLP-1 receptor agonists and cardiovascular outcomes",
        authors=["Smith J", "Lee K"],
        journal="New England Journal of Medicine",
        pub_date="2025-06-01",
        pub_types=["Randomized Controlled Trial"],
        tldr="GLP-1 receptor agonists were associated with fewer major cardiovascular events.",
        why_it_matters=(
            "The abstract suggests the therapy class may improve outcomes beyond glycemic control."
        ),
        key_findings=["Reduced major adverse cardiovascular events in the intervention arm."],
        limitations=["Abstract-level evidence only; subgroup detail is limited."],
    )


def test_digest_accepts_valid_structured_payload() -> None:
    """The top-level Digest model accepts a fully structured payload."""
    digest = Digest(
        query=(
            "What do recent PubMed abstracts suggest about GLP-1 receptor "
            "agonists and cardiovascular outcomes?"
        ),
        paper_cards=[make_paper_card()],
        cross_paper_synthesis=(
            "Across the retrieved abstracts, GLP-1 receptor agonists were "
            "associated with improved cardiovascular outcomes. [PMID:12345678]"
        ),
        citations=[
            Citation(
                pmid="12345678",
                claim="Improved cardiovascular outcomes were reported.",
            )
        ],
        abstentions=[],
    )

    assert digest.paper_cards[0].pmid == "12345678"
    assert digest.citations[0].claim.startswith("Improved")


def test_paper_card_rejects_overlong_tldr() -> None:
    """The schema enforces the ADR's short TLDR constraint."""
    with pytest.raises(ValidationError):
        PaperCard(
            pmid="12345678",
            title="A title",
            authors=["Smith J"],
            journal="Journal",
            pub_date="2025",
            pub_types=["Review"],
            tldr="x" * 281,
            why_it_matters="Why it matters",
            key_findings=[],
            limitations=[],
        )


def test_citation_requires_numeric_pmid() -> None:
    """Citation PMIDs must be closed-set-friendly numeric identifiers."""
    with pytest.raises(ValidationError):
        Citation(pmid="PMID:12345678", claim="This should fail.")


@pytest.mark.parametrize("pub_date", ["2025", "2025-06", "2025-06-01"])
def test_paper_card_accepts_partial_publication_dates(pub_date: str) -> None:
    """PubMed dates may be year-only or year-month, so all three forms pass."""
    card = make_paper_card().model_copy(update={"pub_date": pub_date})
    assert PaperCard.model_validate(card.model_dump()).pub_date == pub_date


@pytest.mark.parametrize("pub_date", ["25", "2025/06/01", "June 2025", "2025-6-1"])
def test_paper_card_rejects_malformed_publication_dates(pub_date: str) -> None:
    """Non-ISO publication dates are rejected rather than silently stored."""
    payload = make_paper_card().model_dump() | {"pub_date": pub_date}
    with pytest.raises(ValidationError):
        PaperCard.model_validate(payload)


def test_models_forbid_unknown_fields_and_strip_whitespace() -> None:
    """Extra keys fail loudly and string fields are whitespace-normalized."""
    with pytest.raises(ValidationError):
        Citation.model_validate({"pmid": "1", "claim": "ok", "source": "llm"})

    citation = Citation(pmid="  42  ", claim="  Stripped claim.  ")
    assert citation.pmid == "42"
    assert citation.claim == "Stripped claim."


def test_digest_requires_at_least_one_paper_card() -> None:
    """A digest with no paper cards has nothing to synthesize and is rejected."""
    with pytest.raises(ValidationError):
        Digest(query="q", paper_cards=[], cross_paper_synthesis="s")


@pytest.mark.parametrize("field", ["authors", "pub_types"])
def test_paper_card_requires_non_empty_author_and_type_lists(field: str) -> None:
    """Authors and publication types are provenance, so empty lists are rejected."""
    empty: list[str] = []
    payload = make_paper_card().model_dump() | {field: empty}
    with pytest.raises(ValidationError):
        PaperCard.model_validate(payload)


def test_paper_card_summary_length_boundaries() -> None:
    """TLDR caps at 280 chars and why_it_matters at 500; the exact limits pass."""
    base = make_paper_card().model_dump()
    card = PaperCard.model_validate(base | {"tldr": "x" * 280, "why_it_matters": "y" * 500})
    assert len(card.tldr) == 280
    assert len(card.why_it_matters) == 500

    with pytest.raises(ValidationError):
        PaperCard.model_validate(base | {"why_it_matters": "y" * 501})


def test_whitespace_only_strings_are_rejected_after_stripping() -> None:
    """Stripping runs before min_length, so blank-looking claims cannot slip through."""
    with pytest.raises(ValidationError):
        Citation(pmid="42", claim="   ")


def test_paper_card_optional_lists_default_to_empty() -> None:
    """Omitted key_findings and limitations default to fresh empty lists."""
    payload = make_paper_card().model_dump()
    del payload["key_findings"], payload["limitations"]
    first = PaperCard.model_validate(payload)
    second = PaperCard.model_validate(payload)
    assert first.key_findings == [] and first.limitations == []
    assert first.key_findings is not second.key_findings
