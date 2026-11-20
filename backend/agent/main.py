"""Точка входа ANANISIM OS.

Запуск:
    pythonw -m uvicorn backend.agent.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .genie_ws import router as genie_ws_router
from .routes import router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "frontend" / "dron_ui"

app = FastAPI(
    title="ANANISIM OS",
    description="Семейная панель DRON × GENIE",
    version="0.2.0",
)

app.include_router(router)
app.include_router(genie_ws_router)

# Статика без агрессивного кэша: фронт обновляется мгновенно.
if FRONTEND.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> Response:
    page = FRONTEND / "index.html"
    if page.is_file():
        return FileResponse(
            page,
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "FRONTEND_MISSING",
                "message": "Интерфейс не найден: frontend/dron_ui/index.html",
                "retryable": False,
            }
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict:
    return {"ok": True}
