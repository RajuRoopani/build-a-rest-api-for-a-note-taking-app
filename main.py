"""
main.py — FastAPI application entry point for the Note-Taking API.

Start the server with:
    uvicorn notes_app.main:app --reload

The app mounts five routers and serves a single-page HTML frontend at GET /.
All data is stored in-memory (see storage.py); no database is required.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

from notes_app.routers import users, notes, tags, notebooks, shares

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Note-Taking API",
    description=(
        "A full-featured REST API for creating, organising, searching, "
        "and sharing notes. All data is stored in-memory."
    ),
    version="1.0.0",
)

# ── Templates ─────────────────────────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ── Router registration ───────────────────────────────────────────────────────

app.include_router(users.router)
app.include_router(notes.router)     # owns /notes/* and /notes/{id}/notebook
app.include_router(tags.router)      # owns /notes/{id}/tags/* and /tags/*
app.include_router(notebooks.router) # owns /notebooks/*
app.include_router(shares.router)    # owns /notes/{id}/share* and /users/{id}/shared

# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend(request: Request) -> HTMLResponse:
    """Serve the single-page HTML frontend."""
    return templates.TemplateResponse("index.html", {"request": request})


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
