"""
routers/shares.py — Note sharing endpoints.

Endpoints
---------
POST   /notes/{note_id}/share             Share note with a user (200)
GET    /notes/{note_id}/shares            List users a note is shared with (200 / 404)
DELETE /notes/{note_id}/share/{user_id}   Unshare note from user (200 / 404)
GET    /users/{user_id}/shared            List notes shared with a user (200 / 404)
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from notes_app import storage
from notes_app.models import NoteOut, ShareOut, ShareRequest

router = APIRouter(tags=["shares"])


def _build_share_out(share: dict) -> ShareOut:
    """Convert a raw storage dict into a ShareOut response model."""
    return ShareOut(**share)


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


def _get_user_or_404(user_id: str) -> dict:
    """Return the user dict or raise HTTP 404."""
    user = storage.users.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )
    return user


@router.post("/notes/{note_id}/share", response_model=ShareOut)
def share_note(note_id: str, body: ShareRequest) -> ShareOut:
    """Share a note with another user.

    Idempotent — sharing the same note with the same user a second time
    returns the existing share record without creating a duplicate.
    Returns 404 if the note or target user does not exist.
    """
    _get_note_or_404(note_id)
    _get_user_or_404(body.user_id)

    # Check for existing share (idempotency)
    for share in storage.shares:
        if share["note_id"] == note_id and share["user_id"] == body.user_id:
            return _build_share_out(share)

    share = {
        "note_id": note_id,
        "user_id": body.user_id,
        "shared_at": datetime.now(tz=timezone.utc),
    }
    storage.shares.append(share)
    return _build_share_out(share)


@router.get("/notes/{note_id}/shares", response_model=List[ShareOut])
def list_note_shares(note_id: str) -> List[ShareOut]:
    """List all share records for a given note.

    Returns 404 if the note does not exist.
    """
    _get_note_or_404(note_id)
    results = [s for s in storage.shares if s["note_id"] == note_id]
    return [_build_share_out(s) for s in results]


@router.delete("/notes/{note_id}/share/{user_id}")
def unshare_note(note_id: str, user_id: str) -> dict:
    """Remove a share between a note and a user.

    Returns 404 if the note, user, or share record does not exist.
    """
    _get_note_or_404(note_id)
    _get_user_or_404(user_id)

    for i, share in enumerate(storage.shares):
        if share["note_id"] == note_id and share["user_id"] == user_id:
            storage.shares.pop(i)
            return {"detail": f"Note '{note_id}' unshared from user '{user_id}'."}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No share record found for note '{note_id}' and user '{user_id}'.",
    )


@router.get("/users/{user_id}/shared", response_model=List[NoteOut])
def list_notes_shared_with_user(user_id: str) -> List[NoteOut]:
    """List all notes shared with a given user.

    Returns 404 if the user does not exist.
    """
    _get_user_or_404(user_id)

    shared_note_ids = {s["note_id"] for s in storage.shares if s["user_id"] == user_id}
    results = [
        _build_note_out(storage.notes[nid])
        for nid in shared_note_ids
        if nid in storage.notes
    ]
    return results
