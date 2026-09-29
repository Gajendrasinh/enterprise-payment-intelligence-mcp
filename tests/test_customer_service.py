"""Unit tests for CustomerService."""

import pytest

from payment_mcp.data.seed import SEED_CUSTOMERS
from payment_mcp.models.customer import Customer, CustomerStatus
from payment_mcp.repositories.customer_repository import (
    CustomerRepository,
    InMemoryCustomerRepository,
)
from payment_mcp.services.customer_service import (
    CustomerNotFound,
    CustomerService,
)
from payment_mcp.services.payment_service import (
    InternalServiceError,
    ValidationError,
)


class FailingCustomerRepository(CustomerRepository):
    """Mock customer repository simulating infrastructure failures."""

    def get_by_id(self, _customer_id: str) -> Customer | None:
        raise RuntimeError("Database connection lost")

    def save(self, _customer: Customer) -> None:
        raise RuntimeError("Database write failed")


@pytest.fixture
def customer_service() -> CustomerService:
    repo = InMemoryCustomerRepository(seed_data=SEED_CUSTOMERS)
    return CustomerService(repository=repo)


def test_get_valid_customer(customer_service: CustomerService) -> None:
    """Verify retrieval of existing customer profile."""
    customer = customer_service.get_customer("CUS-001")
    assert customer.customer_id == "CUS-001"
    assert customer.name == "John Tan"
    assert customer.country == "SG"
    assert customer.status == CustomerStatus.ACTIVE


def test_get_unknown_customer_raises_not_found(customer_service: CustomerService) -> None:
    """Verify CustomerNotFound exception for unknown customer ID."""
    with pytest.raises(CustomerNotFound) as exc_info:
        customer_service.get_customer("CUS-999")
    assert "CUS-999" in str(exc_info.value)


def test_get_customer_empty_id_raises_validation_error(
    customer_service: CustomerService,
) -> None:
    """Verify ValidationError when customer_id is empty."""
    with pytest.raises(ValidationError):
        customer_service.get_customer("")
    with pytest.raises(ValidationError):
        customer_service.get_customer("   ")


def test_customer_service_handles_repository_failure() -> None:
    """Verify InternalServiceError when customer repository raises unexpected exceptions."""
    failing_repo = FailingCustomerRepository()
    service = CustomerService(repository=failing_repo)

    with pytest.raises(InternalServiceError):
        service.get_customer("CUS-001")
