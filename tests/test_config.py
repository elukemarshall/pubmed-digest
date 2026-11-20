"""Tests for runtime config loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pubmed_digest.config import (
    DEFAULT_MODELS_PATH,
    ModelRoute,
    NCBIConfig,
    load_runtime_config,
)


def test_load_runtime_config_reads_models_toml() -> None:
    """The committed models.toml scaffold loads into the runtime config model."""
    config = load_runtime_config()

    assert DEFAULT_MODELS_PATH.name == "models.toml"
    assert config.card.primary.verification_status == "pending"
    assert config.role("synthesis").budget_kind == "per_run"
    assert config.budgets.per_eval_usd == 5.0
    assert config.ncbi.requests_per_second_without_key == 3
    assert config.ncbi.top_k_hard_cap == 25


def test_verified_model_route_requires_date_verified() -> None:
    """A verified route must record when that verification happened."""
    with pytest.raises(ValidationError):
        ModelRoute(
            provider="anthropic",
            model="claude-sonnet-x",
            verification_status="verified",
        )


_VALID_NCBI: dict[str, int] = {
    "requests_per_second_without_key": 3,
    "requests_per_second_with_key": 10,
    "cache_ttl_hours": 24,
    "esearch_retmax_default": 100,
    "esearch_retmax_hard_cap": 500,
    "top_k_default": 10,
    "top_k_hard_cap": 25,
}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requests_per_second_with_key", 2),
        ("esearch_retmax_default", 501),
        ("top_k_default", 26),
    ],
)
def test_ncbi_config_rejects_inverted_caps(field: str, value: int) -> None:
    """Defaults above hard caps, or keyed throughput below anonymous, are rejected."""
    with pytest.raises(ValidationError):
        NCBIConfig.model_validate({**_VALID_NCBI, field: value})


def test_ncbi_config_accepts_defaults_equal_to_caps() -> None:
    """A default equal to its hard cap is the boundary case and stays valid."""
    config = NCBIConfig.model_validate(
        {**_VALID_NCBI, "esearch_retmax_default": 500, "top_k_default": 25}
    )

    assert config.top_k_default == config.top_k_hard_cap
