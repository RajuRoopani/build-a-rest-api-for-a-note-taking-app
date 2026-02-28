"""
routers/notebooks.py — Notebook management endpoints.

Endpoints
---------
POST   /notebooks                      Create a notebook (201)
GET    /notebooks                      List notebooks, optional user_id filter (200)
GET    /notebooks/{notebook_id}        Get a notebook (200 / 404)
DELETE /notebooks/{notebook_id}        Delete notebook; nullifies note.notebook_id (204 / 404)
GET    /notebooks/{notebook_id}/notes  List notes in notebook (200 / 404)
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from notes_app import storage
from notes_app.models import NotebookCreate, NotebookOut, NoteOut

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def _build_notebook_out(nb: dict) -> NotebookOut:
    """Convert a raw storage dict into a NotebookOut response model."""
    return NotebookOut(**nb)


def _build_note_out(note: dict) -> NoteOut:
    """Convert a raw storage dict into a NoteOut response model."""
    return NoteOut(**note)


def _get_notebook_or_404(notebook_id: str) -> dict:
    """Return the notebook dict or raise HTTP 404."""
    nb = storage.notebooks.get(notebook_id)
    if nb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notebook '{notebook_id}' not found.",
        )
    return nb


@router.post("", status_code=status.HTTP_201_CREATED, response_model=NotebookOut)
def create_notebook(body: NotebookCreate) -> NotebookOut:
    """Create a new notebook.

    Returns 404 if the referenced user does not exist.
    """
    if body.user_id not in storage.users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_id}' not found.",
        )

    notebook_id = storage.next_notebook_id()
    now = datetime.now(tz=timezone.utc)
    nb = {
        "id": notebook_id,
        "name": body.name,
        "user_id": body.user_id,
        "created_at": now,
    }
    storage.notebooks[notebook_id] = nb
    return _build_notebook_out(nb)


@router.get("", response_model=List[NotebookOut])
def list_notebooks(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
) -> List[NotebookOut]:
    """List all notebooks with an optional user_id filter."""
    results = list(storage.notebooks.values())
    if user_id is not None:
        results = [nb for nb in results if nb["user_id"] == user_id]
    return [_build_notebook_out(nb) for nb in results]


@router.get("/{notebook_id}", response_model=NotebookOut)
def get_notebook(notebook_id: str) -> NotebookOut:
    """Retrieve a single notebook by ID.

    Returns 404 if not found.
    """
    return _build_notebook_out(_get_notebook_or_404(notebook_id))


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(notebook_id: str) -> None:
    """Delete a notebook.

    All notes previously assigned to this notebook have their notebook_id
    set to None so they are not orphaned.
    Returns 204 on success, 404 if not found.
    """
    _get_notebook_or_404(notebook_id)  # raises 404 if missing
    del storage.notebooks[notebook_id]

    # Nullify notebook_id on all notes that belonged to this notebook
    for note in storage.notes.values():
        if note["notebook_id"] == notebook_id:
            note["notebook_id"] = None


@router.get("/{notebook_id}/notes", response_model=List[NoteOut])
def list_notebook_notes(notebook_id: str) -> List[NoteOut]:
    """List all notes assigned to a given notebook.

    Returns 404 if the notebook does not exist.
    """
    _get_notebook_or_404(notebook_id)  # validate existence
    results = [
        _build_note_out(note)
        for note in storage.notes.values()
        if note["notebook_id"] == notebook_id
    ]
    return results
