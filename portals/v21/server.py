"""FixtureBench portal v21 — virtualized order grid (rows mount only when scrolled into view)."""

from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from portals._shared.templating import render

V21_DIR = Path(__file__).resolve().parent
DATA_PATH = V21_DIR / "data" / "orders.json"
SESSION_COOKIE = "fixturebench_portal_v21_session"


def load_portal_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def create_app() -> FastAPI:
    data = load_portal_data()
    sessions: dict[str, str] = {}
    row_height = int(data.get("row_height", 44))
    viewport_rows = int(data.get("viewport_rows", 8))

    app = FastAPI(title="FixtureBench Portal v21 — Virtualized Grid")
    templates = Jinja2Templates(directory=str(V21_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(V21_DIR / "static")), name="static")

    def _require_auth(request: Request) -> Optional[str]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        return sessions.get(token)

    def _row_summary(order: dict[str, Any]) -> dict[str, Any]:
        return {
            "po_number": order["po_number"],
            "order_date": order["order_date"],
            "status": order["status"],
            "item_count": len(order["lines"]),
            "total_amount": order["total_amount"],
        }

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
        # Intentionally do NOT render order rows server-side — only the virtual shell.
        return render(templates, request, "orders.html", {
                "portal_title": data["buyer"]["portal_title"],
                "user_email": user,
                "total_orders": len(data["orders"]),
                "row_height": row_height,
                "viewport_rows": viewport_rows,
            })

    @app.get("/api/orders/window")
    async def orders_window(request: Request, offset: int = 0, limit: int = 12):
        user = _require_auth(request)
        if not user:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        total = len(data["orders"])
        offset = max(0, offset)
        limit = max(1, min(limit, 30))
        end = min(total, offset + limit)
        rows = [_row_summary(o) for o in data["orders"][offset:end]]
        return JSONResponse(
            {
                "offset": offset,
                "limit": limit,
                "total": total,
                "row_height": row_height,
                "rows": rows,
            }
        )

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

    parser = argparse.ArgumentParser(description="Run FixtureBench portal v21")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8020)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
