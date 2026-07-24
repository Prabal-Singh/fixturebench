"""FixtureBench portal v23 — stale cached PO detail until explicit refresh."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from portals._shared.templating import render

V23_DIR = Path(__file__).resolve().parent
DATA_PATH = V23_DIR / "data" / "orders.json"
SESSION_COOKIE = "fixturebench_portal_v23_session"


def load_portal_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def create_app() -> FastAPI:
    data = load_portal_data()
    sessions: dict[str, str] = {}

    app = FastAPI(title="FixtureBench Portal v23 — Stale Cache")
    templates = Jinja2Templates(directory=str(V23_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(V23_DIR / "static")), name="static")

    def _require_auth(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return sessions.get(token)

    def _find_order(po_number: str) -> Optional[dict[str, Any]]:
        return next((o for o in data["orders"] if o["po_number"] == po_number), None)

    def _want_fresh(request: Request) -> bool:
        if request.query_params.get("fresh") == "1":
            return True
        cache_control = (request.headers.get("cache-control") or "").lower()
        return "no-cache" in cache_control or "max-age=0" in cache_control

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request) -> RedirectResponse:
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        return RedirectResponse(url="/login", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: Optional[str] = None):
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        return render(
            templates,
            request,
            "login.html",
            {
                "portal_title": data["buyer"]["portal_title"],
                "error": "Invalid email or password." if error else None,
            },
        )

    @app.post("/login")
    async def login_submit(
        request: Request, email: str = Form(...), password: str = Form(...)
    ) -> RedirectResponse:
        creds = data["credentials"]
        if email != creds["email"] or password != creds["password"]:
            return RedirectResponse(url="/login?error=1", status_code=302)
        token = secrets.token_urlsafe(32)
        sessions[token] = email
        response = RedirectResponse(url="/orders", status_code=302)
        response.set_cookie(SESSION_COOKIE, token, httponly=True)
        return response

    @app.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        return render(
            templates,
            request,
            "orders.html",
            {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "orders": data["orders"],
            },
        )

    @app.get("/orders/{po_number}", response_class=HTMLResponse)
    async def order_detail(request: Request, po_number: str):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        order = _find_order(po_number)
        if order is None:
            return RedirectResponse(url="/orders", status_code=302)

        fresh = _want_fresh(request)
        display_lines = order["lines"] if fresh else order["stale_lines"]
        return render(
            templates,
            request,
            "order_detail.html",
            {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "buyer_name": data["buyer"]["name"],
                "order": order,
                "display_lines": display_lines,
                "is_fresh": fresh,
                "stale_as_of": order.get("stale_as_of"),
            },
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run FixtureBench portal v23")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8022)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
