"""
tests/test_shares.py — Integration tests for shares router.

Covers:
- POST /notes/{note_id}/share          → 200 / 404, idempotent
- GET  /notes/{note_id}/shares         → 200 / 404
- DELETE /notes/{note_id}/share/{uid}  → 200 / 404
- GET  /users/{user_id}/shared         → 200 / 404
"""

import pytest
from fastapi.testclient import TestClient

from notes_app.main import app
from notes_app import storage


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset():
    """Wipe all in-memory stores before every test."""
    storage.reset_storage()
    yield
    storage.reset_storage()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create_user(client: TestClient, username: str = "alice", email: str = "alice@example.com") -> str:
    r = client.post("/users", json={"username": username, "email": email})
    assert r.status_code == 201
    return r.json()["id"]


def _create_note(client: TestClient, user_id: str) -> str:
    r = client.post("/notes", json={"title": "T", "content": "C", "user_id": user_id})
    assert r.status_code == 201
    return r.json()["id"]


# ── Share a Note ───────────────────────────────────────────────────────────────

def test_share_note_returns_200(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)

    r = client.post(f"/notes/{note_id}/share", json={"user_id": uid2})
    assert r.status_code == 200
    body = r.json()
    assert body["note_id"] == note_id
    assert body["user_id"] == uid2
    assert "shared_at" in body


def test_share_note_unknown_note_returns_404(client: TestClient) -> None:
    uid = _create_user(client)
    r = client.post("/notes/99999/share", json={"user_id": uid})
    assert r.status_code == 404


def test_share_note_unknown_user_returns_404(client: TestClient) -> None:
    uid = _create_user(client)
    note_id = _create_note(client, uid)
    r = client.post(f"/notes/{note_id}/share", json={"user_id": "99999"})
    assert r.status_code == 404


def test_share_note_idempotent_no_duplicate(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)

    r1 = client.post(f"/notes/{note_id}/share", json={"user_id": uid2})
    assert r1.status_code == 200
    shared_at_first = r1.json()["shared_at"]

    r2 = client.post(f"/notes/{note_id}/share", json={"user_id": uid2})
    assert r2.status_code == 200
    # Same record returned — shared_at unchanged
    assert r2.json()["shared_at"] == shared_at_first
    # No duplicate in storage
    duplicates = [
        s for s in storage.shares
        if s["note_id"] == note_id and s["user_id"] == uid2
    ]
    assert len(duplicates) == 1


# ── List Shares ────────────────────────────────────────────────────────────────

def test_list_note_shares_returns_200(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)
    client.post(f"/notes/{note_id}/share", json={"user_id": uid2})

    r = client.get(f"/notes/{note_id}/shares")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["user_id"] == uid2


def test_list_note_shares_unknown_note_returns_404(client: TestClient) -> None:
    r = client.get("/notes/99999/shares")
    assert r.status_code == 404


def test_list_note_shares_empty_when_not_shared(client: TestClient) -> None:
    uid = _create_user(client)
    note_id = _create_note(client, uid)
    r = client.get(f"/notes/{note_id}/shares")
    assert r.status_code == 200
    assert r.json() == []


# ── Unshare ────────────────────────────────────────────────────────────────────

def test_unshare_returns_200(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)
    client.post(f"/notes/{note_id}/share", json={"user_id": uid2})

    r = client.delete(f"/notes/{note_id}/share/{uid2}")
    assert r.status_code == 200


def test_unshare_removes_share_record(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)
    client.post(f"/notes/{note_id}/share", json={"user_id": uid2})
    client.delete(f"/notes/{note_id}/share/{uid2}")

    r = client.get(f"/notes/{note_id}/shares")
    assert r.status_code == 200
    assert r.json() == []


def test_unshare_no_share_record_returns_404(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)

    # Never shared — straight to unshare
    r = client.delete(f"/notes/{note_id}/share/{uid2}")
    assert r.status_code == 404


def test_unshare_unknown_note_returns_404(client: TestClient) -> None:
    uid = _create_user(client)
    r = client.delete(f"/notes/99999/share/{uid}")
    assert r.status_code == 404


def test_unshare_unknown_user_returns_404(client: TestClient) -> None:
    uid = _create_user(client)
    note_id = _create_note(client, uid)
    r = client.delete(f"/notes/{note_id}/share/99999")
    assert r.status_code == 404


# ── Shared With User ───────────────────────────────────────────────────────────

def test_list_shared_with_user_returns_200(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)
    client.post(f"/notes/{note_id}/share", json={"user_id": uid2})

    r = client.get(f"/users/{uid2}/shared")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == note_id


def test_list_shared_with_user_unknown_user_returns_404(client: TestClient) -> None:
    r = client.get("/users/99999/shared")
    assert r.status_code == 404


def test_list_shared_with_user_empty_when_nothing_shared(client: TestClient) -> None:
    uid = _create_user(client)
    r = client.get(f"/users/{uid}/shared")
    assert r.status_code == 200
    assert r.json() == []


def test_list_shared_with_user_after_unshare_is_empty(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    note_id = _create_note(client, uid1)
    client.post(f"/notes/{note_id}/share", json={"user_id": uid2})
    client.delete(f"/notes/{note_id}/share/{uid2}")

    r = client.get(f"/users/{uid2}/shared")
    assert r.status_code == 200
    assert r.json() == []
