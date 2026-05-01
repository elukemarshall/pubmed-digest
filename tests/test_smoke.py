"""Smoke tests — prove the package imports and exposes its basic surface."""

import pubmed_digest


def test_version_is_a_string() -> None:
    """The package exposes __version__ as a non-empty string."""
    assert isinstance(pubmed_digest.__version__, str)
    assert len(pubmed_digest.__version__) > 0


def test_version_matches_expected() -> None:
    """The current package version is 0.1.0."""
    assert pubmed_digest.__version__ == "0.1.0"
