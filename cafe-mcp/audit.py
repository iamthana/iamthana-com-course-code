import json
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from mcp.server.auth.middleware.auth_context import get_access_token

AUDIT_LOG = Path(__file__).parent / "audit.log"

# Argument names whose values are recorded as sent. Every other argument, such as customer_name, becomes "[redacted]".
LOGGED_ARGUMENTS = {"order_id", "items", "menu", "size", "quantity", "max_price_thb", "day"}

# require_scope adds the missing scope here, so the middleware can tell a refusal from other tool errors.
scope_refusals: ContextVar[list[str]] = ContextVar("scope_refusals")


def write_audit(**fields) -> None:
    record = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "request_id": uuid4().hex[:12]}
    record.update({name: value for name, value in fields.items() if value is not None})
    with AUDIT_LOG.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, ensure_ascii=False) + "\n")


def redact(value):
    if isinstance(value, dict):
        return {name: redact(item) if name in LOGGED_ARGUMENTS else "[redacted]" for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


async def audit_middleware(ctx, call_next):
    if ctx.request_id is None:
        return await call_next(ctx)
    params = ctx.params or {}
    access_token = get_access_token()
    refusals: list[str] = []
    scope_refusals.set(refusals)
    outcome = "error"
    try:
        result = await call_next(ctx)
        if refusals:
            outcome = "refused"
        elif result.get("isError"):
            outcome = "error"
        elif result.get("resultType") == "input_required":
            outcome = "input_required"
        else:
            outcome = "ok"
        return result
    finally:
        # params are raw client JSON here: this runs before validation, so check each type before reading it.
        arguments = params.get("arguments")
        responses = params.get("inputResponses")
        write_audit(
            principal=access_token.client_id if access_token else "stdio",
            method=ctx.method,
            name=params.get("name") or params.get("uri"),
            arguments=redact(arguments) if isinstance(arguments, dict) else None,
            answers=[r.get("action") for r in responses.values() if isinstance(r, dict)] if isinstance(responses, dict) else None,
            outcome=outcome,
        )


class HttpAudit:
    """Records every response with status 400 or above, including requests that never reach MCP. Reads the path, never the query string or headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_and_record(message):
            if message["type"] == "http.response.start" and message["status"] >= 400:
                user = scope.get("user")
                write_audit(
                    principal=user.access_token.client_id if user and hasattr(user, "access_token") else "anonymous",
                    method="http",
                    name=f"{scope['method']} {scope['path']}",
                    outcome=f"http_{message['status']}",
                )
            await send(message)

        await self.app(scope, receive, send_and_record if scope["type"] == "http" else send)
