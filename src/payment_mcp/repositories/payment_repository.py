"""Payment repository interface and thread-safe in-memory implementation."""

import threading
from abc import ABC, abstractmethod

from payment_mcp.data.seed import SEED_PAYMENTS
from payment_mcp.models.payment import Payment, PaymentStatus


class PaymentRepository(ABC):
    """Abstract interface defining payment persistence operations."""

    @abstractmethod
    def get_by_id(self, payment_id: str) -> Payment | None:
        """Retrieve payment by unique identifier."""
        raise NotImplementedError

    @abstractmethod
    def find_by_customer_id(
        self,
        customer_id: str,
        status: PaymentStatus | None = None,
    ) -> list[Payment]:
        """Find payments for a customer, optionally filtered by status."""
        raise NotImplementedError

    @abstractmethod
    def save(self, payment: Payment) -> None:
        """Persist or update a payment record."""
        raise NotImplementedError


class InMemoryPaymentRepository(PaymentRepository):
    """Thread-safe in-memory repository for payment records."""

    def __init__(self, seed_data: list[Payment] | None = None) -> None:
        self._lock = threading.Lock()
        self._storage: dict[str, Payment] = {}
        initial_data = seed_data if seed_data is not None else SEED_PAYMENTS
        for payment in initial_data:
            self._storage[payment.payment_id] = payment

    def get_by_id(self, payment_id: str) -> Payment | None:
        """Retrieve payment by ID."""
        with self._lock:
            payment = self._storage.get(payment_id)
            return payment.model_copy() if payment else None

    def find_by_customer_id(
        self,
        customer_id: str,
        status: PaymentStatus | None = None,
    ) -> list[Payment]:
        """Find payments by customer ID with optional status filtering."""
        with self._lock:
            results: list[Payment] = []
            for payment in self._storage.values():
                if payment.customer_id == customer_id and (
                    status is None or payment.status == status
                ):
                    results.append(payment.model_copy())
            return results

    def save(self, payment: Payment) -> None:
        """Save payment to storage."""
        with self._lock:
            self._storage[payment.payment_id] = payment.model_copy()
