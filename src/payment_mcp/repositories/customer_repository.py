"""Customer repository interface and thread-safe in-memory implementation."""

import threading
from abc import ABC, abstractmethod

from payment_mcp.data.seed import SEED_CUSTOMERS
from payment_mcp.models.customer import Customer


class CustomerRepository(ABC):
    """Abstract interface defining customer persistence operations."""

    @abstractmethod
    def get_by_id(self, customer_id: str) -> Customer | None:
        """Retrieve customer by unique identifier."""
        raise NotImplementedError

    @abstractmethod
    def save(self, customer: Customer) -> None:
        """Persist or update a customer record."""
        raise NotImplementedError


class InMemoryCustomerRepository(CustomerRepository):
    """Thread-safe in-memory repository for customer records."""

    def __init__(self, seed_data: list[Customer] | None = None) -> None:
        self._lock = threading.Lock()
        self._storage: dict[str, Customer] = {}
        initial_data = seed_data if seed_data is not None else SEED_CUSTOMERS
        for customer in initial_data:
            self._storage[customer.customer_id] = customer

    def get_by_id(self, customer_id: str) -> Customer | None:
        """Retrieve customer by ID."""
        with self._lock:
            customer = self._storage.get(customer_id)
            return customer.model_copy() if customer else None

    def save(self, customer: Customer) -> None:
        """Save customer to storage."""
        with self._lock:
            self._storage[customer.customer_id] = customer.model_copy()
