"""Payment domain models and schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field


class PaymentStatus(StrEnum):
    """Payment transaction states."""

    SETTLED = "SETTLED"
    DECLINED = "DECLINED"
    PENDING = "PENDING"


class Payment(BaseModel):
    """Payment entity representing a financial transaction."""

    payment_id: str = Field(description="Unique payment identifier (e.g., PAY-1001)")
    customer_id: str = Field(description="Associated customer identifier (e.g., CUS-001)")
    amount: float = Field(description="Transaction monetary amount", gt=0)
    currency: str = Field(description="ISO 4217 currency code (e.g., SGD, USD)")
    status: PaymentStatus = Field(description="Settlement status of transaction")
    merchant: str = Field(description="Merchant or vendor name")
    decline_code: str | None = Field(
        default=None,
        description="ISO 8583 / payment gateway decline reason code",
    )


class PaymentLookupResponse(BaseModel):
    """Structured response for single payment retrieval."""

    found: bool
    payment: Payment | None = None
    error: str | None = None


class CustomerTransactionsResponse(BaseModel):
    """Structured response for searching customer transactions."""

    customer_id: str
    count: int
    transactions: list[Payment]
    error: str | None = None
