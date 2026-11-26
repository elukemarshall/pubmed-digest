"""Tests for runtime config loading and validation."""

from __future__ import annotations

import datetime as dt

import pytest
from pydantic import ValidationError

from pubmed_digest.config import (
    DEFAULT_MODELS_PATH,
    BudgetConfig,
    ModelRoute,
    NCBIConfig,
    RoleConfig,
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


def test_model_route_strips_whitespace_and_rejects_blank_fields() -> None:
    """Provider/model are trimmed, and a whitespace-only value is rejected as empty."""
    route = ModelRoute(provider="  anthropic ", model=" claude-sonnet-x  ")

    assert route.provider == "anthropic"
    assert route.model == "claude-sonnet-x"
    with pytest.raises(ValidationError):
        ModelRoute(provider="   ", model="claude-sonnet-x")


def test_verified_model_route_with_date_is_accepted() -> None:
    """A verified route that records its verification date is valid."""
    route = ModelRoute(
        provider="anthropic",
        model="claude-sonnet-x",
        verification_status="verified",
        date_verified=dt.date(2026, 11, 22),
    )

    assert route.date_verified == dt.date(2026, 11, 22)


def test_load_runtime_config_accepts_str_path_and_role_lookup() -> None:
    """A string path loads the same config, and role() maps names to role blocks."""
    config = load_runtime_config(str(DEFAULT_MODELS_PATH))

    assert config.role("card") is config.card
    assert config.role("synthesis") is config.synthesis


@pytest.mark.parametrize("value", [0, -1.0])
def test_budget_config_rejects_non_positive_caps(value: float) -> None:
    """Spend caps must be strictly positive; zero or negative budgets are rejected."""
    with pytest.raises(ValidationError):
        BudgetConfig(per_run_usd=value, per_eval_usd=5.0)
    with pytest.raises(ValidationError):
        BudgetConfig(per_run_usd=1.0, per_eval_usd=value)


def test_role_config_rejects_unknown_budget_kind_and_extra_fields() -> None:
    """budget_kind is a closed set, and unexpected keys are forbidden."""
    route = {"provider": "anthropic", "model": "claude-sonnet-x"}
    valid = {
        "primary": route,
        "fallback": route,
        "budget_kind": "per_card",
        "budget_usd": 0.05,
    }

    assert RoleConfig.model_validate(valid).budget_kind == "per_card"
    with pytest.raises(ValidationError):
        RoleConfig.model_validate({**valid, "budget_kind": "per_day"})
    with pytest.raises(ValidationError):
        RoleConfig.model_validate({**valid, "temperature": 0.2})
