"""FastAPI application entrypoint for PFTL.

Exposes a FastAPI app with Jinja2 templates, routes for game flow, and a websocket endpoint
for streaming gameplay updates.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .core.config import settings
from .db import Base, engine
from .routers.pages import router as pages_router
from .seed import seed_initial_data


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
TEMPLATES_DIR = APP_DIR / "templates"
APP_STATIC_DIR = APP_DIR / "static"
IMAGES_DIR = TEMPLATES_DIR / "images"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Pascal's Faster Than Light")

    # Ensure DB schema exists
    Base.metadata.create_all(bind=engine)

    # Seed ships/upgrades
    seed_initial_data()

    # Templates and static
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    # App bundled static (CSS, JS, images)
    if APP_STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(APP_STATIC_DIR)), name="static")


    # Serve template images (development convenience)
    if IMAGES_DIR.exists():
        app.mount("/templates/images", StaticFiles(directory=str(IMAGES_DIR)), name="template-images")

    # Routers
    app.include_router(pages_router)

    return app

app = create_app()
