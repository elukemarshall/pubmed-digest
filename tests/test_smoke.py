"""Smoke tests — prove the package imports and exposes its basic surface."""

import fabrica


def test_version_is_a_string() -> None:
    """The package exposes __version__ as a non-empty string."""
    assert isinstance(fabrica.__version__, str)
    assert len(fabrica.__version__) > 0


def test_version_matches_expected() -> None:
    """The current package version is 0.1.0."""
    assert fabrica.__version__ == "0.1.0"
