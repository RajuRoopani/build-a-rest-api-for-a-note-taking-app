"""
routers/users.py — User management endpoints.

Endpoints
---------
POST /users            Create a new user (201)
GET  /users/{user_id}  Retrieve a user by ID (200 / 404)
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, status

from notes_app import storage
from notes_app.models import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


def _build_user_out(user: dict) -> UserOut:
    """Convert a raw storage dict into a UserOut response model."""
    return UserOut(**user)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def create_user(body: UserCreate) -> UserOut:
    """Create a new user.

    Returns 409 if the username is already taken.
    """
    # Uniqueness check on username
    for u in storage.users.values():
        if u["username"].lower() == body.username.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{body.username}' is already taken.",
            )

    user_id = storage.next_user_id()
    now = datetime.now(tz=timezone.utc)
    user = {
        "id": user_id,
        "username": body.username,
        "email": body.email,
        "created_at": now,
    }
    storage.users[user_id] = user
    return _build_user_out(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str) -> UserOut:
    """Retrieve a single user by ID.

    Returns 404 if the user does not exist.
    """
    user = storage.users.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )
    return _build_user_out(user)
