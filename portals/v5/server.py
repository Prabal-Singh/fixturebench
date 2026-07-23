"""FixtureBench portal v5 — PO hidden under All Orders tab."""

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

V5_DIR = Path(__file__).resolve().parent
DATA_PATH = V5_DIR / "data" / "orders.json"
SESSION_COOKIE = "fixturebench_portal_v5_session"


def load_portal_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def create_app() -> FastAPI:
    data = load_portal_data()
    sessions: dict[str, str] = {}

    app = FastAPI(title="FixtureBench Portal v5 — Tab Navigation")
    templates = Jinja2Templates(directory=str(V5_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(V5_DIR / "static")), name="static")

    def _require_auth(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return sessions.get(token)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request) -> RedirectResponse:
        if _require_auth(request):
            return RedirectResponse(url="/orders?tab=open", status_code=302)
        return RedirectResponse(url="/login", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: Optional[str] = None):
        if _require_auth(request):
            return RedirectResponse(url="/orders?tab=open", status_code=302)
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
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
    ) -> RedirectResponse:
        creds = data["credentials"]
        if email != creds["email"] or password != creds["password"]:
            return RedirectResponse(url="/login?error=1", status_code=302)
        token = secrets.token_urlsafe(32)
        sessions[token] = email
        response = RedirectResponse(url="/orders?tab=open", status_code=302)
        response.set_cookie(SESSION_COOKIE, token, httponly=True)
        return response

    @app.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request, tab: str = "open"):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)

        if tab == "open":
            orders = [o for o in data["orders"] if o["status"] == "Open" and o["po_number"] != "PO-1042"]
        elif tab == "all":
            orders = data["orders"]
        else:
            orders = []

        return templates.TemplateResponse(
            "orders.html",
            {
                "request": request,
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "orders": orders,
                "active_tab": tab,
            },
        )

    @app.get("/orders/{po_number}", response_class=HTMLResponse)
    async def order_detail(request: Request, po_number: str):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        order = next((o for o in data["orders"] if o["po_number"] == po_number), None)
        if order is None:
            return RedirectResponse(url="/orders?tab=all", status_code=302)
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

    parser = argparse.ArgumentParser(description="Run FixtureBench portal v5")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8004)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
