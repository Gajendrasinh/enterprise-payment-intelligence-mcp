"""Main FastMCP server for custom-payment-mcp.

Exposes payment investigation tools, resources, and prompt templates to AI agents.
Enforces zero-trust RBAC authorization, PII-scrubbed audit logging, and domain
error handling across all operations.
"""

import time

from mcp.server.mcpserver import MCPServer as FastMCP

from payment_mcp.config import Settings, get_settings
from payment_mcp.data.seed import DECLINE_CODE_POLICY_DOCUMENT
from payment_mcp.logging_config import setup_logging
from payment_mcp.models.payment import Payment
from payment_mcp.models.risk import RiskResult
from payment_mcp.repositories.customer_repository import (
    CustomerRepository,
    InMemoryCustomerRepository,
)
from payment_mcp.repositories.payment_repository import (
    InMemoryPaymentRepository,
    PaymentRepository,
)
from payment_mcp.security.audit import log_audit_event
from payment_mcp.security.authorization import (
    ForbiddenException,
    Permission,
    Role,
    SecurityContext,
    UnauthorizedException,
    get_security_context,
    require_permission,
    set_security_context,
)
from payment_mcp.services.customer_service import (
    CustomerNotFound,
    CustomerService,
)
from payment_mcp.services.payment_service import (
    PaymentNotFound,
    PaymentService,
    ValidationError,
)
from payment_mcp.services.risk_service import (
    RiskEngine,
    RiskService,
    RuleBasedRiskEngine,
)


def _serialize_payment(p: Payment) -> dict[str, str | float | None]:
    """Serialize Payment domain entity to explicit JSON-compatible dictionary."""
    return {
        "payment_id": p.payment_id,
        "customer_id": p.customer_id,
        "amount": p.amount,
        "currency": p.currency,
        "status": p.status.value,
        "merchant": p.merchant,
        "decline_code": p.decline_code,
    }


def create_mcp_server(
    settings: Settings | None = None,
    payment_repo: PaymentRepository | None = None,
    customer_repo: CustomerRepository | None = None,
    risk_engine: RiskEngine | None = None,
) -> FastMCP:
    """Factory function initializing configured FastMCP server instance."""
    app_settings = settings or get_settings()

    # Initialize repositories
    p_repo = payment_repo or InMemoryPaymentRepository()
    c_repo = customer_repo or InMemoryCustomerRepository()

    # Initialize domain services
    payment_service = PaymentService(p_repo)
    customer_service = CustomerService(c_repo)
    risk_service = RiskService(
        payment_service=payment_service,
        risk_engine=risk_engine or RuleBasedRiskEngine(),
    )

    # Initialize FastMCP server
    mcp = FastMCP(
        name=app_settings.app_name,
        instructions=(
            "Enterprise Payment Intelligence Server providing payment investigation, "
            "customer account profiling, risk analysis, and decline resolution."
        ),
    )

    # Tool 1: get_payment_details
    @mcp.tool()
    def get_payment_details(payment_id: str) -> dict[str, object]:
        """Retrieve detailed payment transaction information by payment ID.

        Args:
            payment_id: Unique payment identifier (e.g., 'PAY-1001').

        Returns:
            Dictionary containing found status and payment entity or safe error.
        """
        start_time = time.perf_counter()
        tool_name = "get_payment_details"
        resource_id = payment_id or "UNKNOWN"
        ctx = get_security_context()
        user_id = ctx.user_id if ctx else "ANONYMOUS"

        try:
            require_permission(Permission.READ_PAYMENT)

            payment = payment_service.get_payment(payment_id)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=True,
                duration_ms=duration_ms,
            )
            return {
                "found": True,
                "payment": _serialize_payment(payment),
            }

        except (UnauthorizedException, ForbiddenException) as auth_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type=auth_err.__class__.__name__,
            )
            return {
                "found": False,
                "error": str(auth_err),
                "error_type": "SecurityError",
            }
        except PaymentNotFound as not_found_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="PaymentNotFound",
            )
            return {
                "found": False,
                "error": str(not_found_err),
            }
        except ValidationError as val_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="ValidationError",
            )
            return {
                "found": False,
                "error": str(val_err),
            }
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="InternalServiceError",
            )
            return {
                "found": False,
                "error": "An internal service error occurred while retrieving payment details.",
            }

    # Tool 2: get_customer_details
    @mcp.tool()
    def get_customer_details(customer_id: str) -> dict[str, object]:
        """Retrieve customer account profile and status by customer ID.

        Args:
            customer_id: Unique customer identifier (e.g., 'CUS-001').

        Returns:
            Dictionary containing found status and customer information.
        """
        start_time = time.perf_counter()
        tool_name = "get_customer_details"
        resource_id = customer_id or "UNKNOWN"
        ctx = get_security_context()
        user_id = ctx.user_id if ctx else "ANONYMOUS"

        try:
            require_permission(Permission.READ_CUSTOMER)

            customer = customer_service.get_customer(customer_id)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=True,
                duration_ms=duration_ms,
            )
            return {
                "found": True,
                "customer": {
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "country": customer.country,
                    "status": customer.status.value,
                },
            }

        except (UnauthorizedException, ForbiddenException) as auth_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type=auth_err.__class__.__name__,
            )
            return {
                "found": False,
                "error": str(auth_err),
                "error_type": "SecurityError",
            }
        except CustomerNotFound as not_found_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="CustomerNotFound",
            )
            return {
                "found": False,
                "error": str(not_found_err),
            }
        except ValidationError as val_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="ValidationError",
            )
            return {
                "found": False,
                "error": str(val_err),
            }
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="InternalServiceError",
            )
            return {
                "found": False,
                "error": "An internal service error occurred while retrieving customer details.",
            }

    # Tool 3: find_customer_transactions
    @mcp.tool()
    def find_customer_transactions(
        customer_id: str,
        status: str | None = None,
    ) -> dict[str, object]:
        """Search historical payment transactions for a customer, optionally filtered by status.

        Args:
            customer_id: Unique customer identifier (e.g., 'CUS-001').
            status: Optional filter: 'SETTLED' or 'DECLINED'.

        Returns:
            Dictionary containing customer ID, transaction count, and transaction list.
        """
        start_time = time.perf_counter()
        tool_name = "find_customer_transactions"
        resource_id = customer_id or "UNKNOWN"
        ctx = get_security_context()
        user_id = ctx.user_id if ctx else "ANONYMOUS"

        try:
            require_permission(Permission.SEARCH_TRANSACTIONS)

            transactions = payment_service.find_customer_transactions(
                customer_id=customer_id,
                status_filter=status,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=True,
                duration_ms=duration_ms,
            )
            return {
                "customer_id": customer_id,
                "count": len(transactions),
                "transactions": [_serialize_payment(tx) for tx in transactions],
            }

        except (UnauthorizedException, ForbiddenException) as auth_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type=auth_err.__class__.__name__,
            )
            return {
                "customer_id": customer_id,
                "count": 0,
                "transactions": [],
                "error": str(auth_err),
                "error_type": "SecurityError",
            }
        except ValidationError as val_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="ValidationError",
            )
            return {
                "customer_id": customer_id,
                "count": 0,
                "transactions": [],
                "error": str(val_err),
            }
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="InternalServiceError",
            )
            return {
                "customer_id": customer_id,
                "count": 0,
                "transactions": [],
                "error": "An internal service error occurred while querying transactions.",
            }

    # Tool 4: analyze_payment_risk
    @mcp.tool()
    def analyze_payment_risk(payment_id: str) -> dict[str, object]:
        """Analyze payment risk level using business rules and fraud indicators.

        Args:
            payment_id: Unique payment identifier (e.g., 'PAY-1001').

        Returns:
            Dictionary containing payment ID, assessed risk level, and rationale.
        """
        start_time = time.perf_counter()
        tool_name = "analyze_payment_risk"
        resource_id = payment_id or "UNKNOWN"
        ctx = get_security_context()
        user_id = ctx.user_id if ctx else "ANONYMOUS"

        try:
            require_permission(Permission.ANALYZE_RISK)

            risk_result: RiskResult = risk_service.analyze_payment_risk(payment_id)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=True,
                duration_ms=duration_ms,
            )
            return {
                "payment_id": risk_result.payment_id,
                "risk_level": risk_result.risk_level.value,
                "reason": risk_result.reason,
            }

        except (UnauthorizedException, ForbiddenException) as auth_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type=auth_err.__class__.__name__,
            )
            return {
                "payment_id": payment_id,
                "risk_level": "UNKNOWN",
                "reason": "Authorization check failed",
                "error": str(auth_err),
                "error_type": "SecurityError",
            }
        except PaymentNotFound as not_found_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="PaymentNotFound",
            )
            return {
                "payment_id": payment_id,
                "risk_level": "UNKNOWN",
                "reason": "Payment not found",
                "error": str(not_found_err),
            }
        except ValidationError as val_err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="ValidationError",
            )
            return {
                "payment_id": payment_id,
                "risk_level": "UNKNOWN",
                "reason": "Validation failure",
                "error": str(val_err),
            }
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_audit_event(
                tool_name=tool_name,
                user_id=user_id,
                resource_id=resource_id,
                success=False,
                duration_ms=duration_ms,
                error_type="InternalServiceError",
            )
            return {
                "payment_id": payment_id,
                "risk_level": "UNKNOWN",
                "reason": "An internal service error occurred during risk analysis.",
                "error": "Internal risk evaluation failed.",
            }

    # MCP Resource: policy://payment/decline-codes
    @mcp.resource("policy://payment/decline-codes")
    def decline_codes_policy() -> str:
        """Payment gateway and card network decline reason code policy documentation."""
        return DECLINE_CODE_POLICY_DOCUMENT

    # MCP Prompt: investigate_payment
    @mcp.prompt()
    def investigate_payment(payment_id: str) -> str:
        """Reusable workflow prompt guiding an AI agent through payment investigation."""
        return (
            f"You are an enterprise Payment Investigation AI Agent.\n"
            f"Investigate the payment transaction '{payment_id}' by following these steps:\n\n"
            f"1. Retrieve payment details: Call `get_payment_details` with "
            f"payment_id='{payment_id}'.\n"
            f"2. Retrieve customer details: Use customer_id from payment to call "
            f"`get_customer_details`.\n"
            f"3. Analyze payment risk: Call `analyze_payment_risk` with "
            f"payment_id='{payment_id}'.\n"
            f"4. Check decline-code policy: If declined, read resource "
            f"'policy://payment/decline-codes'.\n"
            f"5. Synthesize transaction history: Optionally call `find_customer_transactions`.\n"
            f"6. Explain the result: Present clear diagnosis with reason, risk, and "
            f"resolution.\n"
            f"7. Distinguish facts from assumptions: Clearly separate verified data "
            f"from inferences.\n"
            f"8. Never invent payment information: Strictly rely on data retrieved from tools.\n"
        )

    return mcp


# Module-level server singleton
server = create_mcp_server()


def main() -> None:
    """Entrypoint for launching the custom-payment-mcp server."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level)

    # Initialize default security context for standalone execution
    if get_security_context() is None:
        try:
            role = Role(settings.default_role.upper())
        except ValueError:
            role = Role.ADMIN
        set_security_context(
            SecurityContext(
                user_id=settings.default_user_id,
                role=role,
            )
        )

    transport_choice = settings.mcp_transport.lower()
    if transport_choice == "sse":
        server.run(transport="sse")
    elif transport_choice == "streamable-http":
        server.run(transport="streamable-http")
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
