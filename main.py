"""Development entrypoint for running PFTL with Uvicorn.

Run: python main.py
Alternatively: uvicorn app.main:app --reload
"""

from __future__ import annotations

import uvicorn

from app.core.config import settings


def main() -> None:
    """Start the development server using Uvicorn."""
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)


if __name__ == "__main__":
    main()
