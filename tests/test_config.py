"""Tests for runtime config loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pubmed_digest.config import DEFAULT_MODELS_PATH, ModelRoute, load_runtime_config


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
