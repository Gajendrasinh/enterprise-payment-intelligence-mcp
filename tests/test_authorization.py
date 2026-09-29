from collections.abc import Iterator

import pytest

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


@pytest.fixture(autouse=True)
def clean_security_context() -> Iterator[None]:
    """Ensure clean security context before and after each test."""
    set_security_context(None)
    yield
    set_security_context(None)


def test_require_permission_unauthenticated() -> None:
    """Calls without active security context must raise UnauthorizedException."""
    with pytest.raises(UnauthorizedException) as exc_info:
        require_permission(Permission.READ_PAYMENT)
    assert "Authentication required" in str(exc_info.value)


def test_read_only_role_permissions() -> None:
    """READ_ONLY role allows payment read and transaction search, denies customer and risk."""
    ctx = SecurityContext(user_id="user-ro", role=Role.READ_ONLY)
    set_security_context(ctx)

    # Allowed
    assert require_permission(Permission.READ_PAYMENT) == ctx
    assert require_permission(Permission.SEARCH_TRANSACTIONS) == ctx

    # Denied
    with pytest.raises(ForbiddenException):
        require_permission(Permission.READ_CUSTOMER)

    with pytest.raises(ForbiddenException):
        require_permission(Permission.ANALYZE_RISK)


def test_customer_support_role_permissions() -> None:
    """CUSTOMER_SUPPORT role allows payments, search, customer details, denies risk."""
    ctx = SecurityContext(user_id="user-cs", role=Role.CUSTOMER_SUPPORT)
    set_security_context(ctx)

    # Allowed
    assert require_permission(Permission.READ_PAYMENT) == ctx
    assert require_permission(Permission.SEARCH_TRANSACTIONS) == ctx
    assert require_permission(Permission.READ_CUSTOMER) == ctx

    # Denied
    with pytest.raises(ForbiddenException):
        require_permission(Permission.ANALYZE_RISK)


def test_analyst_role_permissions() -> None:
    """ANALYST role allows payments, search, risk analysis, denies customer details."""
    ctx = SecurityContext(user_id="user-analyst", role=Role.ANALYST)
    set_security_context(ctx)

    # Allowed
    assert require_permission(Permission.READ_PAYMENT) == ctx
    assert require_permission(Permission.SEARCH_TRANSACTIONS) == ctx
    assert require_permission(Permission.ANALYZE_RISK) == ctx

    # Denied
    with pytest.raises(ForbiddenException):
        require_permission(Permission.READ_CUSTOMER)


def test_admin_role_permissions() -> None:
    """ADMIN role grants full access across all permissions."""
    ctx = SecurityContext(user_id="user-admin", role=Role.ADMIN)
    set_security_context(ctx)

    for perm in Permission:
        assert require_permission(perm) == ctx


def test_security_context_explicit_argument() -> None:
    """require_permission must respect explicitly provided context over ContextVar."""
    ctx_admin = SecurityContext(user_id="admin-01", role=Role.ADMIN)
    ctx_ro = SecurityContext(user_id="ro-01", role=Role.READ_ONLY)

    set_security_context(ctx_admin)

    # Passing ctx_ro explicitly overrides the ambient ctx_admin
    with pytest.raises(ForbiddenException):
        require_permission(Permission.ANALYZE_RISK, context=ctx_ro)


def test_get_and_set_security_context() -> None:
    """Verify context variable propagation and reset."""
    assert get_security_context() is None
    test_ctx = SecurityContext(user_id="test-user", role=Role.ADMIN)
    set_security_context(test_ctx)
    assert get_security_context() == test_ctx
    set_security_context(None)
    assert get_security_context() is None
