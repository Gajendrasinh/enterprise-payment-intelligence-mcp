"""Customer service managing customer account intelligence."""

from payment_mcp.models.customer import Customer
from payment_mcp.repositories.customer_repository import CustomerRepository
from payment_mcp.services.payment_service import (
    InternalServiceError,
    ValidationError,
)


class CustomerServiceError(Exception):
    """Base error for customer service operations."""


class CustomerNotFound(CustomerServiceError):
    """Raised when the specified customer ID does not exist."""


class CustomerService:
    """Service providing customer intelligence and profile retrieval."""

    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    def get_customer(self, customer_id: str) -> Customer:
        """Fetch customer details by customer ID.

        Raises:
            ValidationError: If customer_id is empty or blank.
            CustomerNotFound: If no customer exists with the provided ID.
            InternalServiceError: If repository access fails.
        """
        if not customer_id or not customer_id.strip():
            raise ValidationError("Customer ID must not be empty.")

        try:
            customer = self._repository.get_by_id(customer_id.strip())
        except Exception as exc:
            raise InternalServiceError(f"Failed to query customer repository: {exc}") from exc

        if customer is None:
            raise CustomerNotFound(f"Customer '{customer_id.strip()}' was not found.")

        return customer
