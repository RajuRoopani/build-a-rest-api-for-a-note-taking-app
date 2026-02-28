"""
storage.py — In-memory data store for the Note-Taking API.

All data lives in module-level dicts/lists.  No database is used.
Call reset_storage() between tests to get a clean slate.

Data shapes
-----------
users       : {user_id: {id, username, email, created_at}}
notes       : {note_id: {id, title, content, user_id, created_at, updated_at,
                         is_pinned, is_archived, tags: list[str], notebook_id}}
notebooks   : {notebook_id: {id, name, user_id, created_at}}
shares      : [{note_id, user_id, shared_at}]   — one entry per (note, user) pair
"""

from typing import Dict, List

# ── Primary stores ────────────────────────────────────────────────────────────

users: Dict[str, dict] = {}
notes: Dict[str, dict] = {}
notebooks: Dict[str, dict] = {}
shares: List[dict] = []

# ── Auto-increment counters ───────────────────────────────────────────────────

_user_counter: int = 0
_note_counter: int = 0
_notebook_counter: int = 0


# ── ID generators ─────────────────────────────────────────────────────────────

def next_user_id() -> str:
    """Return the next user ID string and advance the counter."""
    global _user_counter
    _user_counter += 1
    return str(_user_counter)


def next_note_id() -> str:
    """Return the next note ID string and advance the counter."""
    global _note_counter
    _note_counter += 1
    return str(_note_counter)


def next_notebook_id() -> str:
    """Return the next notebook ID string and advance the counter."""
    global _notebook_counter
    _notebook_counter += 1
    return str(_notebook_counter)


# ── Test helper ───────────────────────────────────────────────────────────────

def reset_storage() -> None:
    """Clear all stores and reset counters.  Call this in test fixtures."""
    global _user_counter, _note_counter, _notebook_counter
    users.clear()
    notes.clear()
    notebooks.clear()
    shares.clear()
    _user_counter = 0
    _note_counter = 0
    _notebook_counter = 0
