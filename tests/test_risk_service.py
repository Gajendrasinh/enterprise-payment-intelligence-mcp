"""Unit tests for RiskService and RuleBasedRiskEngine."""

import pytest

from payment_mcp.data.seed import SEED_PAYMENTS
from payment_mcp.models.payment import Payment, PaymentStatus
from payment_mcp.models.risk import RiskLevel, RiskResult
from payment_mcp.repositories.payment_repository import InMemoryPaymentRepository
from payment_mcp.services.payment_service import (
    PaymentNotFound,
    PaymentService,
)
from payment_mcp.services.risk_service import (
    RiskEngine,
    RiskService,
    RuleBasedRiskEngine,
)


@pytest.fixture
def payment_service() -> PaymentService:
    repo = InMemoryPaymentRepository(seed_data=SEED_PAYMENTS)
    return PaymentService(repository=repo)


@pytest.fixture
def risk_service(payment_service: PaymentService) -> RiskService:
    return RiskService(payment_service=payment_service)


def test_analyze_risk_settled_transaction(risk_service: RiskService) -> None:
    """Settled transactions must evaluate to LOW risk."""
    result = risk_service.analyze_payment_risk("PAY-1002")
    assert result.payment_id == "PAY-1002"
    assert result.risk_level == RiskLevel.LOW
    assert "settled successfully" in result.reason.lower()


def test_analyze_risk_declined_medium_value(risk_service: RiskService) -> None:
    """Declined transactions under SGD 1000 threshold must evaluate to MEDIUM risk."""
    result = risk_service.analyze_payment_risk("PAY-1001")
    assert result.payment_id == "PAY-1001"
    assert result.risk_level == RiskLevel.MEDIUM
    assert result.reason == "Transaction was declined"


def test_analyze_risk_high_value_declined(risk_service: RiskService) -> None:
    """Declined transactions >= SGD 1000 threshold must evaluate to HIGH risk."""
    result = risk_service.analyze_payment_risk("PAY-1003")
    assert result.payment_id == "PAY-1003"
    assert result.risk_level == RiskLevel.HIGH
    assert "exceeding SGD 1000.00 threshold" in result.reason
    assert "code: 51" in result.reason


def test_analyze_risk_unknown_payment_raises_not_found(risk_service: RiskService) -> None:
    """Analyzing risk for a non-existent payment must raise PaymentNotFound."""
    with pytest.raises(PaymentNotFound):
        risk_service.analyze_payment_risk("PAY-NONEXISTENT")


def test_custom_pluggable_risk_engine(payment_service: PaymentService) -> None:
    """Verify that RiskService works with an alternative custom RiskEngine implementation."""

    class MockMLRiskEngine(RiskEngine):
        def evaluate(self, payment: Payment) -> RiskResult:
            return RiskResult(
                payment_id=payment.payment_id,
                risk_level=RiskLevel.HIGH,
                reason="ML Model v2 anomaly score: 0.98",
            )

    custom_service = RiskService(
        payment_service=payment_service,
        risk_engine=MockMLRiskEngine(),
    )
    res = custom_service.analyze_payment_risk("PAY-1002")
    assert res.risk_level == RiskLevel.HIGH
    assert "ML Model v2 anomaly score" in res.reason


def test_rule_based_engine_pending_status() -> None:
    """Verify RuleBasedRiskEngine handling of PENDING payment status."""
    engine = RuleBasedRiskEngine()
    pending_payment = Payment(
        payment_id="PAY-9999",
        customer_id="CUS-001",
        amount=100.0,
        currency="SGD",
        status=PaymentStatus.PENDING,
        merchant="TEST STORE",
    )
    result = engine.evaluate(pending_payment)
    assert result.risk_level == RiskLevel.LOW
    assert "pending" in result.reason.lower()
