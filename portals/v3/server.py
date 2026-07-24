"""Coupa-style fake buyer portal v3 — paginated PO list.

Run:
    python portals/v3/server.py
    python portals/v3/server.py --port 8002
"""

from __future__ import annotations

import argparse
import json
import math
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

V3_DIR = Path(__file__).resolve().parent
DATA_PATH = V3_DIR / "data" / "orders.json"
SESSION_COOKIE = "scruffy_portal_v3_session"


def load_portal_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def create_app() -> FastAPI:
    data = load_portal_data()
    sessions: dict[str, str] = {}
    page_size = int(data.get("page_size", 2))

    app = FastAPI(title="Scruffy Fake Buyer Portal v3")
    templates = Jinja2Templates(directory=str(V3_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(V3_DIR / "static")), name="static")

    def _require_auth(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return sessions.get(token)

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request) -> RedirectResponse:
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        return RedirectResponse(url="/login", status_code=302)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: Optional[str] = None):
        if _require_auth(request):
            return RedirectResponse(url="/orders", status_code=302)
        return render(templates, request, "login.html", {
                "portal_title": data["buyer"]["portal_title"],
                "error": "Invalid email or password." if error else None,
            })

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
        response = RedirectResponse(url="/orders", status_code=302)
        response.set_cookie(SESSION_COOKIE, token, httponly=True)
        return response

    @app.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request, page: int = 1):
        user = _require_auth(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)

        all_orders = data["orders"]
        total_pages = max(1, math.ceil(len(all_orders) / page_size))
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        orders = all_orders[start : start + page_size]

        return render(templates, request, "orders.html", {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "orders": orders,
                "page": page,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            })

    @app.get("/orders/{po_number}", response_class=HTMLResponse)
    async def order_detail(request: Request, po_number: str):
        user = _require_auth(request)
        if not user:
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

    parser = argparse.ArgumentParser(description="Run Scruffy fake buyer portal v3")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
