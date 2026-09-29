"""Tests for server main entrypoint and initialization."""

from unittest.mock import MagicMock, patch

from payment_mcp.config import Settings
from payment_mcp.security.authorization import Role, get_security_context, set_security_context
from payment_mcp.server import main


def test_server_main_stdio() -> None:
    """Verify main entrypoint sets default security context and invokes server.run with stdio."""
    set_security_context(None)
    mock_settings = Settings(
        mcp_transport="stdio",
        default_role="CUSTOMER_SUPPORT",
        default_user_id="USR-MAIN-TEST",
    )

    with (
        patch("payment_mcp.server.get_settings", return_value=mock_settings),
        patch("payment_mcp.server.server.run", MagicMock()) as mock_run,
    ):
        main()
        mock_run.assert_called_once_with(transport="stdio")
        ctx = get_security_context()
        assert ctx is not None
        assert ctx.user_id == "USR-MAIN-TEST"
        assert ctx.role == Role.CUSTOMER_SUPPORT


def test_server_main_sse_and_invalid_role_fallback() -> None:
    """Verify main fallback to ADMIN for invalid role string and runs SSE transport."""
    set_security_context(None)
    mock_settings = Settings(
        mcp_transport="sse",
        default_role="INVALID_ROLE_NAME",
        default_user_id="USR-MAIN-FALLBACK",
    )

    with (
        patch("payment_mcp.server.get_settings", return_value=mock_settings),
        patch("payment_mcp.server.server.run", MagicMock()) as mock_run,
    ):
        main()
        mock_run.assert_called_once_with(transport="sse")
        ctx = get_security_context()
        assert ctx is not None
        assert ctx.role == Role.ADMIN
