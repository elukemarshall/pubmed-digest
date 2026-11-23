"""Smoke tests — prove the package imports and exposes its basic surface."""

import pubmed_digest


def test_version_is_a_string() -> None:
    """The package exposes __version__ as a non-empty string."""
    assert isinstance(pubmed_digest.__version__, str)
    assert len(pubmed_digest.__version__) > 0


def test_version_matches_expected() -> None:
    """The current package version is 0.1.0."""
    assert pubmed_digest.__version__ == "0.1.0"


def test_public_api_names_resolve() -> None:
    """Every name in __all__ is importable from the top-level package."""
    for name in pubmed_digest.__all__:
        assert hasattr(pubmed_digest, name), name


def test_top_level_reexports_match_digest_subpackage() -> None:
    """Top-level schema exports are the same objects as pubmed_digest.digest's."""
    from pubmed_digest import digest

    for name in digest.__all__:
        assert getattr(pubmed_digest, name) is getattr(digest, name)
