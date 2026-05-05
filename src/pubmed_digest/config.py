"""Runtime configuration models and loaders for pubmed-digest."""

import datetime as dt
import tomllib
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

type NonEmptyString = Annotated[str, Field(min_length=1)]
type PositiveUsd = Annotated[float, Field(gt=0)]
type PositiveWholeNumber = Annotated[int, Field(gt=0)]
BudgetKind = Literal["per_card", "per_run"]
RoleName = Literal["card", "synthesis"]
VerificationStatus = Literal["pending", "verified"]

DEFAULT_MODELS_PATH = Path(__file__).resolve().parents[2] / "models.toml"


class ModelRoute(BaseModel):
    """One provider/model choice for an LLM role."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: NonEmptyString
    model: NonEmptyString
    verification_status: VerificationStatus = "pending"
    date_verified: dt.date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_verified_date(self) -> Self:
        """Require a verification date once a route is marked as verified."""
        if self.verification_status == "verified" and self.date_verified is None:
            msg = "date_verified is required when verification_status='verified'"
            raise ValueError(msg)
        return self


class RoleConfig(BaseModel):
    """Primary/fallback model routing and budget for a named role."""

    model_config = ConfigDict(extra="forbid")

    primary: ModelRoute
    fallback: ModelRoute
    budget_kind: BudgetKind
    budget_usd: PositiveUsd


class BudgetConfig(BaseModel):
    """Run-level spend caps used by the benchmark and CLI."""

    model_config = ConfigDict(extra="forbid")

    per_run_usd: PositiveUsd
    per_eval_usd: PositiveUsd


class NCBIConfig(BaseModel):
    """NCBI runtime defaults shared by retrieval and fixture capture."""

    model_config = ConfigDict(extra="forbid")

    requests_per_second_without_key: PositiveWholeNumber
    requests_per_second_with_key: PositiveWholeNumber
    cache_ttl_hours: PositiveWholeNumber
    esearch_retmax_default: PositiveWholeNumber
    esearch_retmax_hard_cap: PositiveWholeNumber
    top_k_default: PositiveWholeNumber
    top_k_hard_cap: PositiveWholeNumber

    @model_validator(mode="after")
    def validate_caps(self) -> Self:
        """Keep defaults below hard caps and keyed throughput above anonymous throughput."""
        if self.requests_per_second_with_key < self.requests_per_second_without_key:
            msg = "requests_per_second_with_key must be >= requests_per_second_without_key"
            raise ValueError(msg)
        if self.esearch_retmax_default > self.esearch_retmax_hard_cap:
            msg = "esearch_retmax_default must be <= esearch_retmax_hard_cap"
            raise ValueError(msg)
        if self.top_k_default > self.top_k_hard_cap:
            msg = "top_k_default must be <= top_k_hard_cap"
            raise ValueError(msg)
        return self


class RuntimeConfig(BaseModel):
    """Validated config loaded from ``models.toml``."""

    model_config = ConfigDict(extra="forbid")

    card: RoleConfig
    synthesis: RoleConfig
    budgets: BudgetConfig
    ncbi: NCBIConfig

    def role(self, name: RoleName) -> RoleConfig:
        """Return a role config by name."""
        return self.card if name == "card" else self.synthesis


def load_runtime_config(path: Path | str | None = None) -> RuntimeConfig:
    """Load and validate runtime configuration from TOML."""
    config_path = Path(path) if path is not None else DEFAULT_MODELS_PATH
    with config_path.open("rb") as fh:
        payload = tomllib.load(fh)
    return RuntimeConfig.model_validate(payload)
