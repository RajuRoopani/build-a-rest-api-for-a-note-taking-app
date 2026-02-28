"""
routers/notes.py — Core note CRUD, search, pin/archive, and notebook assignment.

Route order matters!  GET /notes/search MUST be declared before
GET /notes/{note_id} so FastAPI does not interpret the literal string
"search" as a note_id path parameter.

Endpoints
---------
POST   /notes                        Create note (201)
GET    /notes/search?q=<query>       Search notes (200)   ← before /{note_id}
GET    /notes/{note_id}              Get note (200 / 404)
GET    /notes                        List all notes with filters (200)
PUT    /notes/{note_id}              Update note (200 / 404)
DELETE /notes/{note_id}              Delete note (204 / 404)
PATCH  /notes/{note_id}/pin          Toggle pin (200 / 404)
PATCH  /notes/{note_id}/archive      Toggle archive (200 / 404)
PUT    /notes/{note_id}/notebook     Assign notebook (200 / 404)
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from notes_app import storage
from notes_app.models import NoteCreate, NoteNotebookAssign, NoteOut, NoteUpdate

router = APIRouter(tags=["notes"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_note_out(note: dict) -> NoteOut:
    """Convert a raw storage dict into a NoteOut response model."""
    return NoteOut(**note)


def _get_note_or_404(note_id: str) -> dict:
    """Return the note dict or raise HTTP 404."""
    note = storage.notes.get(note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note '{note_id}' not found.",
        )
    return note


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/notes", status_code=status.HTTP_201_CREATED, response_model=NoteOut)
def create_note(body: NoteCreate) -> NoteOut:
    """Create a new note.

    Returns 404 if the referenced user does not exist.
    """
    if body.user_id not in storage.users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_id}' not found.",
        )

    note_id = storage.next_note_id()
    now = datetime.now(tz=timezone.utc)
    note = {
        "id": note_id,
        "title": body.title,
        "content": body.content,
        "user_id": body.user_id,
        "created_at": now,
        "updated_at": now,
        "is_pinned": False,
        "is_archived": False,
        "tags": [],
        "notebook_id": None,
    }
    storage.notes[note_id] = note
    return _build_note_out(note)


# ── Search (MUST be before /{note_id}) ────────────────────────────────────────

@router.get("/notes/search", response_model=List[NoteOut])
def search_notes(q: str = Query(..., description="Search query string")) -> List[NoteOut]:
    """Search notes by a case-insensitive substring match on title and content.

    Returns an empty list when no notes match.
    """
    q_lower = q.lower()
    results = [
        _build_note_out(note)
        for note in storage.notes.values()
        if q_lower in note["title"].lower() or q_lower in note["content"].lower()
    ]
    return results


# ── Get single note ───────────────────────────────────────────────────────────

@router.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: str) -> NoteOut:
    """Retrieve a single note by ID.

    Returns 404 if not found.
    """
    return _build_note_out(_get_note_or_404(note_id))


# ── List notes ────────────────────────────────────────────────────────────────

@router.get("/notes", response_model=List[NoteOut])
def list_notes(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    pinned: Optional[bool] = Query(None, description="Filter pinned notes"),
    archived: Optional[bool] = Query(None, description="Filter archived notes"),
) -> List[NoteOut]:
    """List all notes with optional filters.

    Filters are applied cumulatively (AND logic).
    """
    results = list(storage.notes.values())

    if user_id is not None:
        results = [n for n in results if n["user_id"] == user_id]
    if pinned is not None:
        results = [n for n in results if n["is_pinned"] == pinned]
    if archived is not None:
        results = [n for n in results if n["is_archived"] == archived]

    return [_build_note_out(n) for n in results]


# ── Update note ───────────────────────────────────────────────────────────────

@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: str, body: NoteUpdate) -> NoteOut:
    """Update a note's title and/or content.

    Refreshes updated_at on any change. Returns 404 if not found.
    """
    note = _get_note_or_404(note_id)

    if body.title is not None:
        note["title"] = body.title
    if body.content is not None:
        note["content"] = body.content
    note["updated_at"] = datetime.now(tz=timezone.utc)

    return _build_note_out(note)


# ── Delete note ───────────────────────────────────────────────────────────────

@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str) -> None:
    """Delete a note.

    Also removes all share records for this note.
    Returns 204 on success, 404 if not found.
    """
    _get_note_or_404(note_id)  # raises 404 if missing
    del storage.notes[note_id]

    # Clean up orphaned share records
    storage.shares[:] = [s for s in storage.shares if s["note_id"] != note_id]


# ── Pin / Archive toggles ─────────────────────────────────────────────────────

@router.patch("/notes/{note_id}/pin", response_model=NoteOut)
def toggle_pin(note_id: str) -> NoteOut:
    """Toggle the is_pinned flag on a note.

    Returns the updated note or 404 if not found.
    """
    note = _get_note_or_404(note_id)
    note["is_pinned"] = not note["is_pinned"]
    note["updated_at"] = datetime.now(tz=timezone.utc)
    return _build_note_out(note)


@router.patch("/notes/{note_id}/archive", response_model=NoteOut)
def toggle_archive(note_id: str) -> NoteOut:
    """Toggle the is_archived flag on a note.

    Returns the updated note or 404 if not found.
    """
    note = _get_note_or_404(note_id)
    note["is_archived"] = not note["is_archived"]
    note["updated_at"] = datetime.now(tz=timezone.utc)
    return _build_note_out(note)


# ── Notebook assignment ───────────────────────────────────────────────────────

@router.put("/notes/{note_id}/notebook", response_model=NoteOut)
def assign_notebook(note_id: str, body: NoteNotebookAssign) -> NoteOut:
    """Assign a note to a notebook.

    Returns 404 if either the note or the notebook does not exist.
    """
    note = _get_note_or_404(note_id)

    if body.notebook_id not in storage.notebooks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notebook '{body.notebook_id}' not found.",
        )

    note["notebook_id"] = body.notebook_id
    note["updated_at"] = datetime.now(tz=timezone.utc)
    return _build_note_out(note)
