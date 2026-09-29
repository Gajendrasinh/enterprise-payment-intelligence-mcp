"""Payment service encapsulating payment querying and transaction operations."""

from payment_mcp.models.payment import Payment, PaymentStatus
from payment_mcp.repositories.payment_repository import PaymentRepository


class PaymentServiceError(Exception):
    """Base error for payment service failures."""


class PaymentNotFound(PaymentServiceError):
    """Raised when the specified payment ID does not exist."""


class ValidationError(PaymentServiceError):
    """Raised when client input fails business validation."""


class InternalServiceError(PaymentServiceError):
    """Raised when an unexpected internal failure occurs."""


class PaymentService:
    """Service providing payment retrieval and transaction search capabilities."""

    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    def get_payment(self, payment_id: str) -> Payment:
        """Fetch payment details by ID.

        Raises:
            ValidationError: If payment_id is empty or invalid.
            PaymentNotFound: If no payment exists with the provided ID.
            InternalServiceError: If repository access fails.
        """
        if not payment_id or not payment_id.strip():
            raise ValidationError("Payment ID must not be empty.")

        try:
            payment = self._repository.get_by_id(payment_id.strip())
        except Exception as exc:
            raise InternalServiceError(f"Failed to query payment repository: {exc}") from exc

        if payment is None:
            raise PaymentNotFound(f"Payment '{payment_id.strip()}' was not found.")

        return payment

    def find_customer_transactions(
        self,
        customer_id: str,
        status_filter: str | None = None,
    ) -> list[Payment]:
        """Find transactions for a customer with optional status filter.

        Supported status values: 'SETTLED', 'DECLINED'.

        Raises:
            ValidationError: If customer_id is empty or status is invalid.
            InternalServiceError: If repository access fails.
        """
        if not customer_id or not customer_id.strip():
            raise ValidationError("Customer ID must not be empty.")

        parsed_status: PaymentStatus | None = None
        if status_filter is not None and status_filter.strip():
            clean_status = status_filter.strip().upper()
            try:
                parsed_status = PaymentStatus(clean_status)
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid status '{status_filter}'. Supported statuses: SETTLED, DECLINED"
                ) from exc

        try:
            return self._repository.find_by_customer_id(
                customer_id=customer_id.strip(),
                status=parsed_status,
            )
        except Exception as exc:
            raise InternalServiceError(f"Failed to query transactions repository: {exc}") from exc
