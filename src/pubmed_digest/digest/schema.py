"""Typed digest-domain models for structured pubmed-digest outputs."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

type NonEmptyString = Annotated[str, Field(min_length=1)]
type PMID = Annotated[str, Field(min_length=1, pattern=r"^\d+$")]
type PublicationDate = Annotated[
    str,
    Field(min_length=4, pattern=r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$"),
]
type ShortSummary = Annotated[str, Field(min_length=1, max_length=280)]
type MediumSummary = Annotated[str, Field(min_length=1, max_length=500)]


def empty_strings() -> list[NonEmptyString]:
    """Return an empty list with a stable string-list type."""
    return []


def empty_citations() -> list[Citation]:
    """Return an empty list with a stable citation-list type."""
    return []


class Citation(BaseModel):
    """One citation-grounded claim reference."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pmid: PMID
    claim: NonEmptyString


class PaperCard(BaseModel):
    """Structured per-paper artifact emitted before cross-paper synthesis."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pmid: PMID
    title: NonEmptyString
    authors: list[NonEmptyString] = Field(min_length=1)
    journal: NonEmptyString
    pub_date: PublicationDate
    pub_types: list[NonEmptyString] = Field(min_length=1)
    tldr: ShortSummary
    why_it_matters: MediumSummary
    key_findings: list[NonEmptyString] = Field(default_factory=empty_strings)
    limitations: list[NonEmptyString] = Field(default_factory=empty_strings)


class Digest(BaseModel):
    """Top-level structured digest exported as Markdown or JSON."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: NonEmptyString
    paper_cards: list[PaperCard] = Field(min_length=1)
    cross_paper_synthesis: NonEmptyString
    citations: list[Citation] = Field(default_factory=empty_citations)
    abstentions: list[NonEmptyString] = Field(default_factory=empty_strings)
