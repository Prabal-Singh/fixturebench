"""FixtureBench portal v18 — anti-bot interstitial before orders."""

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

V18_DIR = Path(__file__).resolve().parent
DATA_PATH = V18_DIR / "data" / "orders.json"
SESSION_COOKIE = "fixturebench_portal_v18_session"
VERIFIED_COOKIE = "fixturebench_portal_v18_verified"


def load_portal_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def create_app() -> FastAPI:
    data = load_portal_data()
    sessions: dict[str, str] = {}
    verified: set[str] = set()

    app = FastAPI(title="FixtureBench Portal v18 — Anti-bot Interstitial")
    templates = Jinja2Templates(directory=str(V18_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(V18_DIR / "static")), name="static")

    def _require_auth(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return sessions.get(token)

    def _is_verified(request: Request) -> bool:
        token = request.cookies.get(SESSION_COOKIE)
        return bool(token and token in verified)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request) -> RedirectResponse:
        if _require_auth(request):
            if not _is_verified(request):
                return RedirectResponse(url="/verify", status_code=302)
            return RedirectResponse(url="/orders", status_code=302)
        return RedirectResponse(url="/login", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: Optional[str] = None):
        if _require_auth(request):
            if not _is_verified(request):
                return RedirectResponse(url="/verify", status_code=302)
            return RedirectResponse(url="/orders", status_code=302)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
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
        response = RedirectResponse(url="/verify", status_code=302)
        response.set_cookie(SESSION_COOKIE, token, httponly=True)
        return response

    @app.get("/verify", response_class=HTMLResponse)
    async def verify_page(request: Request):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if _is_verified(request):
            return RedirectResponse(url="/orders", status_code=302)
        return templates.TemplateResponse(
            "verify.html",
            {
                "request": request,
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
            },
        )

    @app.post("/verify")
    async def verify_submit(request: Request) -> RedirectResponse:
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            verified.add(token)
        response = RedirectResponse(url="/orders", status_code=302)
        response.set_cookie(VERIFIED_COOKIE, "1", httponly=True)
        return response

    @app.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if not _is_verified(request):
            return RedirectResponse(url="/verify", status_code=302)
        return templates.TemplateResponse(
            "orders.html",
            {
                "request": request,
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
        if not _is_verified(request):
            return RedirectResponse(url="/verify", status_code=302)
        order = next((o for o in data["orders"] if o["po_number"] == po_number), None)
        if order is None:
            return RedirectResponse(url="/orders", status_code=302)
        return templates.TemplateResponse(
            "order_detail.html",
            {
                "request": request,
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "buyer_name": data["buyer"]["name"],
                "order": order,
            },
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run FixtureBench portal v18")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8017)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
