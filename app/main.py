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
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"


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

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Routers
    app.include_router(pages_router)

    return app

app = create_app()
