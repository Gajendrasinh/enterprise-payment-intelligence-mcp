"""Security and Role-Based Access Control (RBAC) module.

Enforces zero-trust authorization where LLM/Agent inputs cannot manipulate
caller identity or permissions. Identity and roles are managed via verified
security contexts (e.g., downstream from OAuth2/OIDC/JWT tokens).
"""

from contextvars import ContextVar
from enum import StrEnum

from pydantic import BaseModel, Field


class SecurityException(Exception):
    """Base exception for security-related failures."""


class UnauthorizedException(SecurityException):
    """Raised when an unauthenticated caller attempts an operation."""


class ForbiddenException(SecurityException):
    """Raised when an authenticated caller lacks required permissions."""


class Role(StrEnum):
    """Predefined enterprise roles."""

    ADMIN = "ADMIN"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    ANALYST = "ANALYST"
    READ_ONLY = "READ_ONLY"


class Permission(StrEnum):
    """Granular action permissions."""

    READ_PAYMENT = "payment:read"
    READ_CUSTOMER = "customer:read"
    SEARCH_TRANSACTIONS = "transactions:search"
    ANALYZE_RISK = "risk:analyze"


# Map each role to its granted permissions
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.READ_ONLY: {
        Permission.READ_PAYMENT,
        Permission.SEARCH_TRANSACTIONS,
    },
    Role.CUSTOMER_SUPPORT: {
        Permission.READ_PAYMENT,
        Permission.SEARCH_TRANSACTIONS,
        Permission.READ_CUSTOMER,
    },
    Role.ANALYST: {
        Permission.READ_PAYMENT,
        Permission.SEARCH_TRANSACTIONS,
        Permission.ANALYZE_RISK,
    },
    Role.ADMIN: {
        Permission.READ_PAYMENT,
        Permission.SEARCH_TRANSACTIONS,
        Permission.READ_CUSTOMER,
        Permission.ANALYZE_RISK,
    },
}


class SecurityContext(BaseModel):
    """Verified principal identity and claims.

    In production, this context is populated exclusively by upstream authentication
    middleware (e.g., verifying JWT signature, issuer, and claims) and never from
    untrusted LLM prompt arguments.
    """

    user_id: str = Field(description="Unique identifier of the authenticated caller")
    role: Role = Field(description="Assigned role for access control")
    token_claims: dict[str, str] = Field(
        default_factory=dict,
        description="Verified claims from JWT or OIDC token",
    )

    def has_permission(self, permission: Permission) -> bool:
        """Check if principal's role grants the requested permission."""
        granted = ROLE_PERMISSIONS.get(self.role, set())
        return permission in granted


# Context variable for thread-safe / coroutine-safe security propagation
_current_context: ContextVar[SecurityContext | None] = ContextVar(
    "current_security_context",
    default=None,
)


def get_security_context() -> SecurityContext | None:
    """Retrieve the current coroutine's active security context."""
    return _current_context.get()


def set_security_context(context: SecurityContext | None) -> None:
    """Set the current coroutine's active security context."""
    _current_context.set(context)


def require_permission(
    permission: Permission,
    context: SecurityContext | None = None,
) -> SecurityContext:
    """Validate that the caller is authenticated and possesses the required permission.

    Raises:
        UnauthorizedException: If no active security context is present.
        ForbiddenException: If the caller role lacks the requested permission.
    """
    ctx = context if context is not None else get_security_context()
    if ctx is None:
        raise UnauthorizedException("Authentication required: No verified security context found.")

    if not ctx.has_permission(permission):
        raise ForbiddenException(
            f"Access denied: Role '{ctx.role.value}' does not have permission '{permission.value}'."
        )

    return ctx
