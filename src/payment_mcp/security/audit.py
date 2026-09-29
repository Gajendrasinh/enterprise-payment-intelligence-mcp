"""Audit logging and security telemetry module.

Captures structured audit events for every MCP invocation, enforces PII / secret
scrubbing, and collects observability metrics for telemetry integrations.
"""

import json
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import ParamSpec, TypeVar

from pydantic import BaseModel, Field

from payment_mcp.security.authorization import (
    ForbiddenException,
    SecurityContext,
    UnauthorizedException,
    get_security_context,
)

logger = logging.getLogger("payment_mcp.audit")

# Deny-list for keys that must never appear in audit logs or metadata
SENSITIVE_FIELD_NAMES = {
    "password",
    "secret",
    "token",
    "access_token",
    "api_key",
    "authorization",
    "private_key",
    "credit_card",
    "cvv",
    "pan",
    "ssn",
}


class AuditEvent(BaseModel):
    """Structured audit trail record for tool invocations."""

    timestamp: str = Field(description="ISO 8601 UTC execution timestamp")
    tool_name: str = Field(description="Name of the MCP tool invoked")
    user_id: str = Field(description="Principal user identifier")
    resource_id: str = Field(description="Target resource identifier")
    success: bool = Field(description="True if invocation succeeded")
    duration_ms: float = Field(description="Execution latency in milliseconds")
    error_type: str | None = Field(default=None, description="Category of error if failed")


class MetricsCollector:
    """Thread-safe metrics accumulator for MCP tool telemetry."""

    def __init__(self) -> None:
        self.invocation_counts: dict[str, int] = defaultdict(int)
        self.error_counts: dict[str, int] = defaultdict(int)
        self.auth_failure_counts: dict[str, int] = defaultdict(int)
        self.total_duration_ms: dict[str, float] = defaultdict(float)

    def record_invocation(self, tool_name: str) -> None:
        """Increment tool invocation count."""
        self.invocation_counts[tool_name] += 1

    def record_error(self, tool_name: str) -> None:
        """Increment tool error count."""
        self.error_counts[tool_name] += 1

    def record_auth_failure(self, tool_name: str) -> None:
        """Increment authorization failure count."""
        self.auth_failure_counts[tool_name] += 1

    def record_duration(self, tool_name: str, duration_ms: float) -> None:
        """Accumulate latency duration."""
        self.total_duration_ms[tool_name] += duration_ms

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        """Return metrics snapshot dictionary."""
        tools = set(self.invocation_counts.keys()) | set(self.error_counts.keys())
        stats: dict[str, dict[str, float | int]] = {}
        for tool in tools:
            invocations = self.invocation_counts[tool]
            errors = self.error_counts[tool]
            auth_fails = self.auth_failure_counts[tool]
            tot_duration = self.total_duration_ms[tool]
            avg_latency = (tot_duration / invocations) if invocations > 0 else 0.0
            stats[tool] = {
                "invocations": invocations,
                "errors": errors,
                "auth_failures": auth_fails,
                "average_latency_ms": round(avg_latency, 2),
            }
        return stats


# Global metrics collector instance
metrics = MetricsCollector()


def sanitize_value(key: str, value: object) -> object:
    """Mask or redact sensitive fields."""
    if any(secret_term in key.lower() for secret_term in SENSITIVE_FIELD_NAMES):
        return "[REDACTED]"
    return value


def log_audit_event(
    tool_name: str,
    user_id: str,
    resource_id: str,
    success: bool,
    duration_ms: float,
    error_type: str | None = None,
) -> AuditEvent:
    """Record an immutable structured audit log entry."""
    now_iso = datetime.now(UTC).isoformat()
    event = AuditEvent(
        timestamp=now_iso,
        tool_name=tool_name,
        user_id=user_id,
        resource_id=resource_id,
        success=success,
        duration_ms=round(duration_ms, 2),
        error_type=error_type,
    )

    # Log as structured JSON
    log_data = event.model_dump()
    logger.info(json.dumps(log_data))

    # Update telemetry metrics
    metrics.record_invocation(tool_name)
    metrics.record_duration(tool_name, duration_ms)
    if not success:
        metrics.record_error(tool_name)
        if error_type in ("UnauthorizedException", "ForbiddenException"):
            metrics.record_auth_failure(tool_name)

    return event


P = ParamSpec("P")
R = TypeVar("R")


def audited_tool(
    tool_name: str,
    resource_extractor: Callable[..., str],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to audit tool execution with execution timing and error capture."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            resource_id = "UNKNOWN"
            try:
                resource_id = resource_extractor(*args, **kwargs)
            except Exception:
                resource_id = "EXTRACTION_FAILED"

            ctx: SecurityContext | None = get_security_context()
            user_id = ctx.user_id if ctx else "ANONYMOUS"

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                log_audit_event(
                    tool_name=tool_name,
                    user_id=user_id,
                    resource_id=resource_id,
                    success=True,
                    duration_ms=duration_ms,
                    error_type=None,
                )
                return result
            except (UnauthorizedException, ForbiddenException) as auth_err:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                err_type = auth_err.__class__.__name__
                log_audit_event(
                    tool_name=tool_name,
                    user_id=user_id,
                    resource_id=resource_id,
                    success=False,
                    duration_ms=duration_ms,
                    error_type=err_type,
                )
                raise
            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                err_type = exc.__class__.__name__
                log_audit_event(
                    tool_name=tool_name,
                    user_id=user_id,
                    resource_id=resource_id,
                    success=False,
                    duration_ms=duration_ms,
                    error_type=err_type,
                )
                raise

        return wrapper

    return decorator
