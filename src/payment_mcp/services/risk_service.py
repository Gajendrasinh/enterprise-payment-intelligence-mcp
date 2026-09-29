"""Risk assessment service and modular risk evaluation engine.

Implements an isolated risk engine interface allowing seamless transition from
deterministic heuristic rules to machine learning scoring models or external
fraud risk APIs.
"""

from abc import ABC, abstractmethod

from payment_mcp.models.payment import Payment, PaymentStatus
from payment_mcp.models.risk import RiskLevel, RiskResult
from payment_mcp.services.payment_service import PaymentService


class RiskEngine(ABC):
    """Abstract risk scoring engine interface.

    Allows interchangeable implementations: rule-based, ML model, or SaaS API.
    """

    @abstractmethod
    def evaluate(self, payment: Payment) -> RiskResult:
        """Evaluate payment transaction risk and produce structured assessment."""
        raise NotImplementedError


class RuleBasedRiskEngine(RiskEngine):
    """Deterministic business rule evaluation engine.

    Rules:
    1. SETTLED transactions -> LOW risk.
    2. DECLINED transactions >= 1000.00 currency units -> HIGH risk.
    3. DECLINED transactions < 1000.00 currency units -> MEDIUM risk.
    """

    HIGH_VALUE_THRESHOLD: float = 1000.00

    def evaluate(self, payment: Payment) -> RiskResult:
        """Evaluate payment risk using deterministic rule set."""
        if payment.status == PaymentStatus.SETTLED:
            return RiskResult(
                payment_id=payment.payment_id,
                risk_level=RiskLevel.LOW,
                reason="Transaction settled successfully without risk flags",
            )

        if payment.status == PaymentStatus.DECLINED:
            if payment.amount >= self.HIGH_VALUE_THRESHOLD:
                decline_info = f" (code: {payment.decline_code})" if payment.decline_code else ""
                return RiskResult(
                    payment_id=payment.payment_id,
                    risk_level=RiskLevel.HIGH,
                    reason=(
                        f"High-value declined transaction exceeding {payment.currency} "
                        f"{self.HIGH_VALUE_THRESHOLD:.2f} threshold{decline_info}"
                    ),
                )
            # Standard declined transaction
            return RiskResult(
                payment_id=payment.payment_id,
                risk_level=RiskLevel.MEDIUM,
                reason="Transaction was declined",
            )

        # Default fallback for pending or unrecognized status
        return RiskResult(
            payment_id=payment.payment_id,
            risk_level=RiskLevel.LOW,
            reason="Transaction is in pending state",
        )


class RiskService:
    """Orchestrates risk evaluation for payment transactions."""

    def __init__(
        self,
        payment_service: PaymentService,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self._payment_service = payment_service
        self._risk_engine = risk_engine or RuleBasedRiskEngine()

    def analyze_payment_risk(self, payment_id: str) -> RiskResult:
        """Analyze risk for a payment identified by payment_id.

        Raises:
            PaymentNotFound: If the payment does not exist.
            ValidationError: If payment_id is invalid.
        """
        payment = self._payment_service.get_payment(payment_id)
        return self._risk_engine.evaluate(payment)
