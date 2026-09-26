"""
Umily — FastAPI Application Entry Point

Creates the FastAPI app, registers routes, mounts the frontend,
initializes the database, and configures middleware.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.config import settings, BASE_DIR
from app.database.database import init_db
from app.logging_config import setup_logging

# --- Route imports ---
from app.api.routes_commands import router as commands_router
from app.api.routes_voice import router as voice_router
from app.api.routes_permissions import router as permissions_router
from app.api.routes_tasks import router as tasks_router
from app.api.routes_system import router as system_router


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""

    # --- Startup ---
    setup_logging()
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    init_db()
    logger.info("Database initialized")

    gemini_ok = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
    logger.info(f"Gemini API configured: {gemini_ok}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Server: http://{settings.HOST}:{settings.PORT}")
    logger.info("=" * 60)

    yield

    # --- Shutdown ---
    logger.info("Umily shutting down…")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Voice-first, permission-controlled AI computer agent for Windows.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API routes (all under /api prefix)
# ---------------------------------------------------------------------------

app.include_router(commands_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(permissions_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(system_router, prefix="/api")


# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------

frontend_dir = BASE_DIR / "frontend"

# Mount CSS and JS as static file directories
if (frontend_dir / "css").exists():
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
if (frontend_dir / "js").exists():
    app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")
if (frontend_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the Umily Control Center frontend."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Umily is running. Frontend not found — place index.html in /frontend."}


# ---------------------------------------------------------------------------
# Run with: python -m uvicorn app.main:app --reload
# ---------------------------------------------------------------------------
