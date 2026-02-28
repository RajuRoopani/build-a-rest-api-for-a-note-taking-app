"""
models.py — Pydantic request / response models for the Note-Taking API.

Naming convention
-----------------
*Create   : incoming request body for POST endpoints
*Update   : incoming request body for PUT / PATCH endpoints
*Out      : outgoing response shape (always returned from endpoints)
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


# ── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Request body for POST /users."""

    username: str
    email: str


class UserOut(BaseModel):
    """Response shape for user endpoints."""

    id: str
    username: str
    email: str
    created_at: datetime


# ── Notes ─────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    """Request body for POST /notes."""

    title: str
    content: str
    user_id: str


class NoteUpdate(BaseModel):
    """Request body for PUT /notes/{note_id}."""

    title: Optional[str] = None
    content: Optional[str] = None


class NoteOut(BaseModel):
    """Response shape for note endpoints."""

    id: str
    title: str
    content: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    is_pinned: bool
    is_archived: bool
    tags: List[str]
    notebook_id: Optional[str]


# ── Tags ──────────────────────────────────────────────────────────────────────

class TagAdd(BaseModel):
    """Request body for POST /notes/{note_id}/tags."""

    label: str


# ── Notebooks ─────────────────────────────────────────────────────────────────

class NotebookCreate(BaseModel):
    """Request body for POST /notebooks."""

    name: str
    user_id: str


class NotebookOut(BaseModel):
    """Response shape for notebook endpoints."""

    id: str
    name: str
    user_id: str
    created_at: datetime


class NoteNotebookAssign(BaseModel):
    """Request body for PUT /notes/{note_id}/notebook."""

    notebook_id: str


# ── Shares ────────────────────────────────────────────────────────────────────

class ShareRequest(BaseModel):
    """Request body for POST /notes/{note_id}/share."""

    user_id: str


class ShareOut(BaseModel):
    """Response shape for a single share record."""

    note_id: str
    user_id: str
    shared_at: datetime
