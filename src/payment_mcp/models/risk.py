"""Risk evaluation domain models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """Categorical risk assessment rating."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskResult(BaseModel):
    """Risk evaluation response for a payment transaction."""

    payment_id: str = Field(description="Evaluated payment identifier")
    risk_level: RiskLevel = Field(description="Assessed risk rating: LOW, MEDIUM, or HIGH")
    reason: str = Field(description="Deterministic rationale explaining the risk score")
    error: str | None = Field(default=None, description="Error detail if evaluation failed")
