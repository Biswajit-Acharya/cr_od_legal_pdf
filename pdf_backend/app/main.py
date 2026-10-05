"""
FastAPI application entry point.

Creates and configures the app instance, registers middleware,
routes, and lifespan events.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import settings
from app.core.constants import API_DESCRIPTION, API_TITLE, API_VERSION
from app.lifespan import lifespan
from app.middleware.exception_handler import register_exception_handler
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.api import routes
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_origin_regex=r"https://.*\.vercel\.app", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

register_exception_handler(app)

# ── Raise Starlette's multipart upload limit to 500 MB ──────────────────────
# Starlette 1.x uses MultiPartParser.max_part_size (default: 1 MB).
# spool_max_size controls when to spool to disk vs keeping in memory.
from starlette.formparsers import MultiPartParser
MultiPartParser.max_part_size = 500 * 1024 * 1024   # 500 MB hard limit
MultiPartParser.spool_max_size = 10 * 1024 * 1024   # spool to disk after 10 MB

from app.core.paths import TEMP_PROCESSING_DIR
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True)

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
app.mount("/temp", StaticFiles(directory=str(TEMP_PROCESSING_DIR)), name="temp")

app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(api_router)

# ── React Frontend Serving ──────────────────────────────────────────
# Serve the built React frontend from frontend/dist/
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse

    # Mount built assets (JS, CSS, images) under /assets/
    _FRONTEND_ASSETS = _FRONTEND_DIST / "assets"
    if _FRONTEND_ASSETS.exists():
        app.mount("/assets", StaticFiles(directory=str(_FRONTEND_ASSETS)), name="frontend_assets")

    # Mount public static files (favicon, manifest, etc.)
    _FRONTEND_STATIC = _FRONTEND_DIST / "static"
    if _FRONTEND_STATIC.exists():
        app.mount("/static/frontend", StaticFiles(directory=str(_FRONTEND_STATIC)), name="frontend_static")

    @app.get("/{full_path:path}")
    async def serve_react_frontend(full_path: str):
        """Catch-all: serve React SPA for any non-API, non-static route."""
        # Skip API routes and existing page routes
        if full_path.startswith("api/") or full_path.startswith("document-management/") or full_path.startswith("v1/") or full_path.startswith("pdf/") or full_path.startswith("convert-to-pdf/") or full_path.startswith("convert-from-pdf/") or full_path.startswith("pdf-copyright-protection/") or full_path.startswith("organize_pdf_services/") or full_path.startswith("ai/") or full_path.startswith("accessibility/") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi"):
            return None
        # Try to serve the exact file from dist
        file_path = _FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Fallback to index.html for SPA routing
        index_file = _FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend not built yet. Run: cd frontend && npm run build"}

