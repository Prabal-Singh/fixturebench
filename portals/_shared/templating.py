"""Jinja TemplateResponse helper compatible with Starlette's (request, name, context) API."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response


def render(
    templates: Jinja2Templates,
    request: Request,
    name: str,
    context: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
) -> Response:
    payload = dict(context or {})
    payload.setdefault("request", request)
    return templates.TemplateResponse(
        request,
        name,
        payload,
        status_code=status_code,
    )
