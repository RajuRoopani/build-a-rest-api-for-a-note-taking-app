"""
routers/tags.py — Tag management endpoints.

Endpoints
---------
POST   /notes/{note_id}/tags           Add a tag to a note (200)
DELETE /notes/{note_id}/tags/{tag}     Remove a tag from a note (200 / 404)
GET    /tags                           List all unique tags across all notes (200)
GET    /tags/{tag}/notes               List notes that have a given tag (200)
"""

from typing import List

from fastapi import APIRouter, HTTPException, status

from notes_app import storage
from notes_app.models import NoteOut, TagAdd

router = APIRouter(tags=["tags"])


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


@router.post("/notes/{note_id}/tags", response_model=NoteOut)
def add_tag(note_id: str, body: TagAdd) -> NoteOut:
    """Add a tag label to a note.

    Duplicate tags are silently ignored (idempotent).
    Returns the updated note or 404 if the note does not exist.
    """
    note = _get_note_or_404(note_id)

    label = body.label.strip()
    if label not in note["tags"]:
        note["tags"].append(label)

    return _build_note_out(note)


@router.delete("/notes/{note_id}/tags/{tag}", response_model=NoteOut)
def remove_tag(note_id: str, tag: str) -> NoteOut:
    """Remove a tag from a note.

    Returns 404 if the note does not exist or if the tag is not on the note.
    """
    note = _get_note_or_404(note_id)

    if tag not in note["tags"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag '{tag}' not found on note '{note_id}'.",
        )

    note["tags"].remove(tag)
    return _build_note_out(note)


@router.get("/tags", response_model=List[str])
def list_all_tags() -> List[str]:
    """Return a deduplicated, sorted list of all tags across every note."""
    all_tags: set = set()
    for note in storage.notes.values():
        all_tags.update(note["tags"])
    return sorted(all_tags)


@router.get("/tags/{tag}/notes", response_model=List[NoteOut])
def list_notes_by_tag(tag: str) -> List[NoteOut]:
    """Return all notes that contain the given tag (exact match)."""
    results = [
        _build_note_out(note)
        for note in storage.notes.values()
        if tag in note["tags"]
    ]
    return results
