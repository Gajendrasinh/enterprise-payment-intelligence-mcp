"""Unit tests for PaymentService."""

import pytest

from payment_mcp.data.seed import SEED_PAYMENTS
from payment_mcp.models.payment import Payment, PaymentStatus
from payment_mcp.repositories.payment_repository import (
    InMemoryPaymentRepository,
    PaymentRepository,
)
from payment_mcp.services.payment_service import (
    InternalServiceError,
    PaymentNotFound,
    PaymentService,
    ValidationError,
)


class FailingPaymentRepository(PaymentRepository):
    """Mock repository that simulates internal persistence failures."""

    def get_by_id(self, _payment_id: str) -> Payment | None:
        raise RuntimeError("Database connection timed out")

    def find_by_customer_id(
        self,
        _customer_id: str,
        _status: PaymentStatus | None = None,
    ) -> list[Payment]:
        raise RuntimeError("Database read failed")

    def save(self, _payment: Payment) -> None:
        raise RuntimeError("Database write failed")


@pytest.fixture
def payment_service() -> PaymentService:
    repo = InMemoryPaymentRepository(seed_data=SEED_PAYMENTS)
    return PaymentService(repository=repo)


def test_get_valid_payment(payment_service: PaymentService) -> None:
    """Verify retrieval of existing payment."""
    payment = payment_service.get_payment("PAY-1001")
    assert payment.payment_id == "PAY-1001"
    assert payment.customer_id == "CUS-001"
    assert payment.amount == 250.00
    assert payment.currency == "SGD"
    assert payment.status == PaymentStatus.DECLINED
    assert payment.merchant == "APPLE"
    assert payment.decline_code == "05"


def test_get_unknown_payment_raises_not_found(payment_service: PaymentService) -> None:
    """Verify PaymentNotFound exception for non-existent payment ID."""
    with pytest.raises(PaymentNotFound) as exc_info:
        payment_service.get_payment("PAY-UNKNOWN")
    assert "PAY-UNKNOWN" in str(exc_info.value)


def test_get_payment_empty_id_raises_validation_error(payment_service: PaymentService) -> None:
    """Verify ValidationError when payment_id is empty or whitespace."""
    with pytest.raises(ValidationError):
        payment_service.get_payment("")
    with pytest.raises(ValidationError):
        payment_service.get_payment("   ")


def test_find_customer_transactions_all(payment_service: PaymentService) -> None:
    """Verify retrieval of all transactions for a customer."""
    transactions = payment_service.find_customer_transactions("CUS-001")
    assert len(transactions) == 2
    ids = {t.payment_id for t in transactions}
    assert ids == {"PAY-1001", "PAY-1003"}


def test_find_customer_transactions_settled(payment_service: PaymentService) -> None:
    """Verify filtering transactions by SETTLED status."""
    tx_cus1 = payment_service.find_customer_transactions("CUS-001", status_filter="SETTLED")
    assert len(tx_cus1) == 0

    tx_cus2 = payment_service.find_customer_transactions("CUS-002", status_filter="SETTLED")
    assert len(tx_cus2) == 1
    assert tx_cus2[0].payment_id == "PAY-1002"
    assert tx_cus2[0].status == PaymentStatus.SETTLED


def test_find_customer_transactions_declined(payment_service: PaymentService) -> None:
    """Verify filtering transactions by DECLINED status."""
    tx_cus1 = payment_service.find_customer_transactions("CUS-001", status_filter="DECLINED")
    assert len(tx_cus1) == 2
    for tx in tx_cus1:
        assert tx.status == PaymentStatus.DECLINED


def test_find_customer_transactions_invalid_status(payment_service: PaymentService) -> None:
    """Verify ValidationError when status filter is unrecognized."""
    with pytest.raises(ValidationError) as exc_info:
        payment_service.find_customer_transactions("CUS-001", status_filter="INVALID_STATUS")
    assert "Supported statuses: SETTLED, DECLINED" in str(exc_info.value)


def test_find_customer_transactions_empty_customer_id(payment_service: PaymentService) -> None:
    """Verify ValidationError when customer_id is empty."""
    with pytest.raises(ValidationError):
        payment_service.find_customer_transactions("")


def test_payment_service_handles_repository_failure() -> None:
    """Verify InternalServiceError when repository fails unexpectedly."""
    failing_repo = FailingPaymentRepository()
    service = PaymentService(repository=failing_repo)

    with pytest.raises(InternalServiceError):
        service.get_payment("PAY-1001")

    with pytest.raises(InternalServiceError):
        service.find_customer_transactions("CUS-001")
