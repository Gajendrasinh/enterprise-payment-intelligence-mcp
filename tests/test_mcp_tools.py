"""End-to-end unit and integration tests for MCP Tools, Resources, and Prompts."""

from collections.abc import Iterator

import pytest
from mcp.server.mcpserver import MCPServer as FastMCP
from mcp.types import CallToolResult, GetPromptResult

from payment_mcp.security.audit import metrics
from payment_mcp.security.authorization import (
    Role,
    SecurityContext,
    set_security_context,
)
from payment_mcp.server import create_mcp_server


@pytest.fixture
def mcp_server() -> FastMCP:
    """Create isolated MCP server for testing."""
    return create_mcp_server()


@pytest.fixture(autouse=True)
def default_admin_context() -> Iterator[None]:
    """Set default ADMIN context for tests, clean up afterwards."""
    ctx = SecurityContext(user_id="test-admin-user", role=Role.ADMIN)
    set_security_context(ctx)
    yield
    set_security_context(None)


@pytest.mark.asyncio
async def test_tool_get_payment_details_found(mcp_server: FastMCP) -> None:
    """Tool 1: get_payment_details returns expected schema for existing payment."""
    result = await mcp_server.call_tool("get_payment_details", {"payment_id": "PAY-1001"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False

    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is True
    payment = data["payment"]
    assert isinstance(payment, dict)
    assert payment["payment_id"] == "PAY-1001"
    assert payment["customer_id"] == "CUS-001"
    assert payment["amount"] == 250.00
    assert payment["currency"] == "SGD"
    assert payment["status"] == "DECLINED"
    assert payment["merchant"] == "APPLE"
    assert payment["decline_code"] == "05"


@pytest.mark.asyncio
async def test_tool_get_payment_details_not_found(mcp_server: FastMCP) -> None:
    """Tool 1: get_payment_details returns safe error when payment does not exist."""
    result = await mcp_server.call_tool("get_payment_details", {"payment_id": "PAY-NONEXISTENT"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is False
    assert "not found" in str(data["error"]).lower()


@pytest.mark.asyncio
async def test_tool_get_payment_details_empty_id(mcp_server: FastMCP) -> None:
    """Tool 1: get_payment_details handles validation errors safely."""
    result = await mcp_server.call_tool("get_payment_details", {"payment_id": "   "})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_tool_get_customer_details_found(mcp_server: FastMCP) -> None:
    """Tool 2: get_customer_details returns customer info for valid ID."""
    result = await mcp_server.call_tool("get_customer_details", {"customer_id": "CUS-001"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is True
    customer = data["customer"]
    assert isinstance(customer, dict)
    assert customer["customer_id"] == "CUS-001"
    assert customer["name"] == "John Tan"
    assert customer["country"] == "SG"
    assert customer["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_tool_get_customer_details_not_found(mcp_server: FastMCP) -> None:
    """Tool 2: get_customer_details returns safe error for unknown customer."""
    result = await mcp_server.call_tool("get_customer_details", {"customer_id": "CUS-999"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is False
    assert "not found" in str(data["error"]).lower()


@pytest.mark.asyncio
async def test_tool_get_customer_details_rbac_forbidden(mcp_server: FastMCP) -> None:
    """Tool 2: get_customer_details rejects READ_ONLY role."""
    set_security_context(SecurityContext(user_id="read-only-user", role=Role.READ_ONLY))

    result = await mcp_server.call_tool("get_customer_details", {"customer_id": "CUS-001"})
    assert isinstance(result, CallToolResult)
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is False
    assert data.get("error_type") == "SecurityError"
    assert "Access denied" in str(data["error"])


@pytest.mark.asyncio
async def test_tool_get_customer_details_unauthenticated(mcp_server: FastMCP) -> None:
    """Tool 2: get_customer_details rejects unauthenticated caller."""
    set_security_context(None)

    result = await mcp_server.call_tool("get_customer_details", {"customer_id": "CUS-001"})
    assert isinstance(result, CallToolResult)
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["found"] is False
    assert "Authentication required" in str(data["error"])


@pytest.mark.asyncio
async def test_tool_find_customer_transactions_all(mcp_server: FastMCP) -> None:
    """Tool 3: find_customer_transactions returns all transactions when status is omitted."""
    result = await mcp_server.call_tool(
        "find_customer_transactions",
        {"customer_id": "CUS-001"},
    )
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["customer_id"] == "CUS-001"
    assert data["count"] == 2
    tx_list = data["transactions"]
    assert isinstance(tx_list, list)
    assert len(tx_list) == 2


@pytest.mark.asyncio
async def test_tool_find_customer_transactions_status_filter(mcp_server: FastMCP) -> None:
    """Tool 3: find_customer_transactions filters by SETTLED and DECLINED."""
    res_declined = await mcp_server.call_tool(
        "find_customer_transactions",
        {"customer_id": "CUS-001", "status": "DECLINED"},
    )
    assert isinstance(res_declined, CallToolResult)
    data_declined = res_declined.structured_content
    assert isinstance(data_declined, dict)
    assert data_declined["count"] == 2

    res_settled = await mcp_server.call_tool(
        "find_customer_transactions",
        {"customer_id": "CUS-001", "status": "SETTLED"},
    )
    assert isinstance(res_settled, CallToolResult)
    data_settled = res_settled.structured_content
    assert isinstance(data_settled, dict)
    assert data_settled["count"] == 0

    res_cus2_settled = await mcp_server.call_tool(
        "find_customer_transactions",
        {"customer_id": "CUS-002", "status": "SETTLED"},
    )
    assert isinstance(res_cus2_settled, CallToolResult)
    data_cus2 = res_cus2_settled.structured_content
    assert isinstance(data_cus2, dict)
    assert data_cus2["count"] == 1


@pytest.mark.asyncio
async def test_tool_find_customer_transactions_invalid_status(mcp_server: FastMCP) -> None:
    """Tool 3: find_customer_transactions returns safe error on invalid status."""
    result = await mcp_server.call_tool(
        "find_customer_transactions",
        {"customer_id": "CUS-001", "status": "UNKNOWN_STATUS"},
    )
    assert isinstance(result, CallToolResult)
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["count"] == 0
    assert "error" in data


@pytest.mark.asyncio
async def test_tool_analyze_payment_risk_medium(mcp_server: FastMCP) -> None:
    """Tool 4: analyze_payment_risk assesses PAY-1001 as MEDIUM risk."""
    result = await mcp_server.call_tool("analyze_payment_risk", {"payment_id": "PAY-1001"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["payment_id"] == "PAY-1001"
    assert data["risk_level"] == "MEDIUM"
    assert data["reason"] == "Transaction was declined"


@pytest.mark.asyncio
async def test_tool_analyze_payment_risk_settled_low(mcp_server: FastMCP) -> None:
    """Tool 4: analyze_payment_risk assesses PAY-1002 as LOW risk."""
    result = await mcp_server.call_tool("analyze_payment_risk", {"payment_id": "PAY-1002"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["payment_id"] == "PAY-1002"
    assert data["risk_level"] == "LOW"


@pytest.mark.asyncio
async def test_tool_analyze_payment_risk_high_value(mcp_server: FastMCP) -> None:
    """Tool 4: analyze_payment_risk assesses high-value decline (PAY-1003) as HIGH risk."""
    result = await mcp_server.call_tool("analyze_payment_risk", {"payment_id": "PAY-1003"})
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["payment_id"] == "PAY-1003"
    assert data["risk_level"] == "HIGH"
    assert "threshold" in str(data["reason"]).lower()


@pytest.mark.asyncio
async def test_tool_analyze_payment_risk_rbac_forbidden(mcp_server: FastMCP) -> None:
    """Tool 4: analyze_payment_risk rejects CUSTOMER_SUPPORT role."""
    set_security_context(SecurityContext(user_id="cs-rep-1", role=Role.CUSTOMER_SUPPORT))

    result = await mcp_server.call_tool("analyze_payment_risk", {"payment_id": "PAY-1001"})
    assert isinstance(result, CallToolResult)
    data = result.structured_content
    assert isinstance(data, dict)
    assert data["risk_level"] == "UNKNOWN"
    assert data["error_type"] == "SecurityError"
    assert "Access denied" in str(data["error"])


@pytest.mark.asyncio
async def test_mcp_resource_decline_codes(mcp_server: FastMCP) -> None:
    """Resource: policy://payment/decline-codes provides decline guidance documentation."""
    resources = await mcp_server.list_resources()
    resource_uris = [str(r.uri) for r in resources]
    assert "policy://payment/decline-codes" in resource_uris

    contents = await mcp_server.read_resource("policy://payment/decline-codes")
    assert isinstance(contents, list)
    assert len(contents) > 0
    text_content = str(contents[0].content)
    assert "05 - Do not honor" in text_content
    assert "51 - Insufficient funds" in text_content
    assert "14 - Invalid card number" in text_content
    assert "54 - Expired card" in text_content
    assert "57 - Transaction not permitted" in text_content


@pytest.mark.asyncio
async def test_mcp_prompt_investigate_payment(mcp_server: FastMCP) -> None:
    """Prompt: investigate_payment provides structured agent investigation instructions."""
    prompts = await mcp_server.list_prompts()
    prompt_names = [p.name for p in prompts]
    assert "investigate_payment" in prompt_names

    prompt_res = await mcp_server.get_prompt("investigate_payment", {"payment_id": "PAY-1001"})
    assert isinstance(prompt_res, GetPromptResult)
    assert len(prompt_res.messages) == 1
    prompt_text = getattr(prompt_res.messages[0].content, "text", "")
    assert "PAY-1001" in prompt_text
    assert "get_payment_details" in prompt_text
    assert "get_customer_details" in prompt_text
    assert "analyze_payment_risk" in prompt_text
    assert "policy://payment/decline-codes" in prompt_text
    assert "Distinguish facts from assumptions" in prompt_text
    assert "Never invent payment information" in prompt_text


def test_audit_and_metrics_accumulation() -> None:
    """Verify that MetricsCollector captures tool invocations and telemetry."""
    snapshot = metrics.snapshot()
    assert isinstance(snapshot, dict)
    assert "get_payment_details" in snapshot
    assert snapshot["get_payment_details"]["invocations"] > 0
    assert snapshot["get_payment_details"]["average_latency_ms"] >= 0
