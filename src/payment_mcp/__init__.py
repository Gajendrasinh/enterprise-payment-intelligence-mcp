"""custom-payment-mcp package."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from payment_mcp.server import create_mcp_server, server

__version__ = "0.1.0"
__all__ = ["create_mcp_server", "server"]


def __getattr__(name: str) -> object:
    if name in ("create_mcp_server", "server"):
        from payment_mcp.server import create_mcp_server as _create_mcp_server
        from payment_mcp.server import server as _server

        if name == "create_mcp_server":
            return _create_mcp_server
        return _server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
