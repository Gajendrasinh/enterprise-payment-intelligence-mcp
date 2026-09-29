"""Customer domain models and schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field


class CustomerStatus(StrEnum):
    """Customer account lifecycle status."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class Customer(BaseModel):
    """Customer entity representation."""

    customer_id: str = Field(description="Unique customer identifier (e.g., CUS-001)")
    name: str = Field(description="Full legal or registered customer name")
    country: str = Field(description="ISO 3166-1 alpha-2 country code (e.g., SG)")
    status: CustomerStatus = Field(description="Current account status")


class CustomerLookupResponse(BaseModel):
    """Structured response for customer retrieval."""

    found: bool
    customer: Customer | None = None
    error: str | None = None
