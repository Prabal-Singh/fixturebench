"""FixtureBench portal v20 — MFA / OTP handoff after password login."""

from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from portals._shared.templating import render

V20_DIR = Path(__file__).resolve().parent
DATA_PATH = V20_DIR / "data" / "orders.json"
SESSION_COOKIE = "fixturebench_portal_v20_session"
# Deterministic OTP for eval agents (documented in case goal).
EXPECTED_OTP = "424242"


def load_portal_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def create_app() -> FastAPI:
    data = load_portal_data()
    # token -> email for password-authenticated but MFA-pending sessions
    pending_mfa: dict[str, str] = {}
    # token -> email for fully authenticated sessions
    sessions: dict[str, str] = {}

    app = FastAPI(title="FixtureBench Portal v20 — MFA Handoff")
    templates = Jinja2Templates(directory=str(V20_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(V20_DIR / "static")), name="static")

    def _require_auth(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return sessions.get(token)

    def _pending_email(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return pending_mfa.get(token)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request) -> RedirectResponse:
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        if _pending_email(request):
            return RedirectResponse(url="/mfa", status_code=302)
        return RedirectResponse(url="/login", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: Optional[str] = None):
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        if _pending_email(request):
            return RedirectResponse(url="/mfa", status_code=302)
        return render(templates, request, "login.html", {
                "portal_title": data["buyer"]["portal_title"],
                "error": "Invalid email or password." if error else None,
            })

    @app.post("/login")
    async def login_submit(
        request: Request, email: str = Form(...), password: str = Form(...)
    ) -> RedirectResponse:
        creds = data["credentials"]
        if email != creds["email"] or password != creds["password"]:
            return RedirectResponse(url="/login?error=1", status_code=302)
        token = secrets.token_urlsafe(32)
        pending_mfa[token] = email
        response = RedirectResponse(url="/mfa", status_code=302)
        response.set_cookie(SESSION_COOKIE, token, httponly=True)
        return response

    @app.get("/mfa", response_class=HTMLResponse)
    async def mfa_page(request: Request, error: Optional[str] = None):
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        email = _pending_email(request)
        if not email:
            return RedirectResponse(url="/login", status_code=302)
        return render(templates, request, "mfa.html", {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": email,
                "error": "Invalid verification code." if error else None,
            })

    @app.post("/mfa")
    async def mfa_submit(request: Request, code: str = Form(...)) -> RedirectResponse:
        email = _pending_email(request)
        if not email:
            return RedirectResponse(url="/login", status_code=302)
        token = request.cookies.get(SESSION_COOKIE)
        if code.strip() != EXPECTED_OTP:
            return RedirectResponse(url="/mfa?error=1", status_code=302)
        if token:
            pending_mfa.pop(token, None)
            sessions[token] = email
        return RedirectResponse(url="/orders", status_code=302)

    @app.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request):
        user = _require_auth(request)
        if not user:
            if _pending_email(request):
                return RedirectResponse(url="/mfa", status_code=302)
            return RedirectResponse(url="/login", status_code=302)
        return render(templates, request, "orders.html", {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "orders": data["orders"],
            })

    @app.get("/orders/{po_number}", response_class=HTMLResponse)
    async def order_detail(request: Request, po_number: str):
        user = _require_auth(request)
        if not user:
            if _pending_email(request):
                return RedirectResponse(url="/mfa", status_code=302)
            return RedirectResponse(url="/login", status_code=302)
        order = next((o for o in data["orders"] if o["po_number"] == po_number), None)
        if order is None:
            return RedirectResponse(url="/orders", status_code=302)
        return render(templates, request, "order_detail.html", {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "buyer_name": data["buyer"]["name"],
                "order": order,
            })

    return app


app = create_app()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run FixtureBench portal v20")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8019)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
