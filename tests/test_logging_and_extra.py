"""Tests for logging configuration, repository save, and audit decorator."""

import logging

import pytest
from mcp.types import CallToolResult

from payment_mcp.logging_config import JSONFormatter, setup_logging
from payment_mcp.models.customer import Customer, CustomerStatus
from payment_mcp.models.payment import Payment, PaymentStatus
from payment_mcp.repositories.customer_repository import InMemoryCustomerRepository
from payment_mcp.repositories.payment_repository import InMemoryPaymentRepository
from payment_mcp.security.audit import (
    audited_tool,
    sanitize_value,
)
from payment_mcp.security.authorization import (
    ForbiddenException,
    Role,
    SecurityContext,
    set_security_context,
)
from payment_mcp.server import create_mcp_server


def test_json_formatter_and_setup_logging() -> None:
    """Verify JSONFormatter produces valid structured JSON and handles custom extras."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message with extra",
        args=(),
        exc_info=None,
    )
    record.__dict__["extra_key"] = "extra_value"
    record.__dict__["ignored_attr"] = {"complex": "dict"}

    output = formatter.format(record)
    assert '"message": "Test message with extra"' in output
    assert '"extra_key": "extra_value"' in output

    setup_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_repository_save_operations() -> None:
    """Verify save methods for Payment and Customer repositories."""
    p_repo = InMemoryPaymentRepository([])
    new_payment = Payment(
        payment_id="PAY-NEW",
        customer_id="CUS-NEW",
        amount=199.99,
        currency="SGD",
        status=PaymentStatus.SETTLED,
        merchant="TEST STORE",
    )
    p_repo.save(new_payment)
    retrieved = p_repo.get_by_id("PAY-NEW")
    assert retrieved is not None
    assert retrieved.payment_id == "PAY-NEW"

    c_repo = InMemoryCustomerRepository([])
    new_customer = Customer(
        customer_id="CUS-NEW",
        name="Alice Wong",
        country="SG",
        status=CustomerStatus.ACTIVE,
    )
    c_repo.save(new_customer)
    retrieved_c = c_repo.get_by_id("CUS-NEW")
    assert retrieved_c is not None
    assert retrieved_c.name == "Alice Wong"


def test_sanitize_value() -> None:
    """Verify sanitization of sensitive keywords."""
    assert sanitize_value("password", "supersecret") == "[REDACTED]"
    assert sanitize_value("api_key", "sk-12345") == "[REDACTED]"
    assert sanitize_value("access_token", "jwt.token") == "[REDACTED]"
    assert sanitize_value("customer_id", "CUS-001") == "CUS-001"


def test_audited_tool_decorator_success_and_errors() -> None:
    """Verify audited_tool decorator captures success, auth errors, and general exceptions."""
    set_security_context(SecurityContext(user_id="audit-tester", role=Role.ADMIN))

    @audited_tool(tool_name="test_tool", resource_extractor=lambda x: str(x))
    def success_op(item_id: str) -> str:
        return f"result-{item_id}"

    assert success_op("item-1") == "result-item-1"

    @audited_tool(tool_name="test_tool_auth_fail", resource_extractor=lambda: "res-1")
    def auth_fail_op() -> None:
        raise ForbiddenException("Access forbidden")

    with pytest.raises(ForbiddenException):
        auth_fail_op()

    @audited_tool(tool_name="test_tool_generic_fail", resource_extractor=lambda: "res-2")
    def generic_fail_op() -> None:
        raise ValueError("General failure")

    with pytest.raises(ValueError):
        generic_fail_op()

    @audited_tool(
        tool_name="test_tool_bad_extractor",
        resource_extractor=lambda: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    def bad_extractor_op() -> str:
        return "ok"

    assert bad_extractor_op() == "ok"


@pytest.mark.asyncio
async def test_tool_internal_error_handling() -> None:
    """Verify tool catches unexpected internal errors and returns safe sanitized response."""

    class BrokenPaymentRepo(InMemoryPaymentRepository):
        def get_by_id(self, _payment_id: str) -> Payment | None:
            raise Exception("Critical internal database crash")

        def find_by_customer_id(
            self,
            _customer_id: str,
            _status: PaymentStatus | None = None,
        ) -> list[Payment]:
            raise Exception("Critical internal database crash")

    class BrokenCustomerRepo(InMemoryCustomerRepository):
        def get_by_id(self, _customer_id: str) -> Customer | None:
            raise Exception("Critical customer DB crash")

    broken_server = create_mcp_server(
        payment_repo=BrokenPaymentRepo([]),
        customer_repo=BrokenCustomerRepo([]),
    )
    set_security_context(SecurityContext(user_id="admin-test", role=Role.ADMIN))

    res1 = await broken_server.call_tool("get_payment_details", {"payment_id": "PAY-1001"})
    assert isinstance(res1, CallToolResult)
    data1 = res1.structured_content
    assert isinstance(data1, dict)
    assert data1["found"] is False
    assert "internal service error" in str(data1["error"]).lower()

    res2 = await broken_server.call_tool("get_customer_details", {"customer_id": "CUS-001"})
    assert isinstance(res2, CallToolResult)
    data2 = res2.structured_content
    assert isinstance(data2, dict)
    assert data2["found"] is False
    assert "internal service error" in str(data2["error"]).lower()

    res3 = await broken_server.call_tool("find_customer_transactions", {"customer_id": "CUS-001"})
    assert isinstance(res3, CallToolResult)
    data3 = res3.structured_content
    assert isinstance(data3, dict)
    assert data3["count"] == 0
    assert "internal service error" in str(data3["error"]).lower()

    res4 = await broken_server.call_tool("analyze_payment_risk", {"payment_id": "PAY-1001"})
    assert isinstance(res4, CallToolResult)
    data4 = res4.structured_content
    assert isinstance(data4, dict)
    assert data4["risk_level"] == "UNKNOWN"
    assert "failed" in str(data4["error"]).lower()
