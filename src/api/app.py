"""aws-billing FastAPI app.

Serves API under /api/v1/ + the React SPA as static files (with index.html
fallback for client-side routing).
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Allow `from config...` and `from src...` regardless of cwd
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from config.settings import settings  # noqa: E402
from src.api import auth as auth_module  # noqa: E402
from src.api.routers import accounts, summary, sync, trends  # noqa: E402
from src.db.pool import close_pool, init_pool  # noqa: E402

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(_project_root) / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="aws-billing", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.auth_enabled,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_module.router, prefix="/api/v1", tags=["auth"])
app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
app.include_router(summary.router, prefix="/api/v1", tags=["summary"])
app.include_router(trends.router, prefix="/api/v1", tags=["trends"])
app.include_router(sync.router, prefix="/api/v1", tags=["sync"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the SPA — assets directory first, then index.html fallback.
if STATIC_DIR.is_dir():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(_request: Request, full_path: str):
        # Don't shadow API routes
        if full_path.startswith("api/"):
            return FileResponse(STATIC_DIR / "index.html", status_code=404)
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
