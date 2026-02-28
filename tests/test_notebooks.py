"""
tests/test_notebooks.py — Integration tests for notebooks router.

Covers:
- POST /notebooks → 201
- GET  /notebooks (all + user_id filter) → 200
- GET  /notebooks/{id} → 200 / 404
- DELETE /notebooks/{id} → 204 / 404, cascade nullifies note.notebook_id
- GET  /notebooks/{id}/notes → 200 / 404
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


def _create_notebook(client: TestClient, user_id: str, name: str = "My Notebook") -> str:
    r = client.post("/notebooks", json={"name": name, "user_id": user_id})
    assert r.status_code == 201
    return r.json()["id"]


def _create_note(client: TestClient, user_id: str) -> str:
    r = client.post("/notes", json={"title": "T", "content": "C", "user_id": user_id})
    assert r.status_code == 201
    return r.json()["id"]


# ── Create ─────────────────────────────────────────────────────────────────────

def test_create_notebook_returns_201(client: TestClient) -> None:
    uid = _create_user(client)
    r = client.post("/notebooks", json={"name": "Work", "user_id": uid})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Work"
    assert body["user_id"] == uid
    assert "id" in body
    assert "created_at" in body


def test_create_notebook_unknown_user_returns_404(client: TestClient) -> None:
    r = client.post("/notebooks", json={"name": "X", "user_id": "99999"})
    assert r.status_code == 404


# ── List ───────────────────────────────────────────────────────────────────────

def test_list_notebooks_returns_all(client: TestClient) -> None:
    uid = _create_user(client)
    _create_notebook(client, uid, "NB1")
    _create_notebook(client, uid, "NB2")
    r = client.get("/notebooks")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_notebooks_user_id_filter(client: TestClient) -> None:
    uid1 = _create_user(client, "alice", "alice@example.com")
    uid2 = _create_user(client, "bob", "bob@example.com")
    _create_notebook(client, uid1, "Alice NB")
    _create_notebook(client, uid2, "Bob NB")

    r = client.get(f"/notebooks?user_id={uid1}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["user_id"] == uid1


def test_list_notebooks_unknown_user_filter_returns_empty(client: TestClient) -> None:
    uid = _create_user(client)
    _create_notebook(client, uid)
    r = client.get("/notebooks?user_id=99999")
    assert r.status_code == 200
    assert r.json() == []


# ── Get ────────────────────────────────────────────────────────────────────────

def test_get_notebook_returns_200(client: TestClient) -> None:
    uid = _create_user(client)
    nb_id = _create_notebook(client, uid, "My NB")
    r = client.get(f"/notebooks/{nb_id}")
    assert r.status_code == 200
    assert r.json()["id"] == nb_id


def test_get_notebook_not_found_returns_404(client: TestClient) -> None:
    r = client.get("/notebooks/99999")
    assert r.status_code == 404


# ── Delete ─────────────────────────────────────────────────────────────────────

def test_delete_notebook_returns_204(client: TestClient) -> None:
    uid = _create_user(client)
    nb_id = _create_notebook(client, uid)
    r = client.delete(f"/notebooks/{nb_id}")
    assert r.status_code == 204


def test_delete_notebook_not_found_returns_404(client: TestClient) -> None:
    r = client.delete("/notebooks/99999")
    assert r.status_code == 404


def test_delete_notebook_cascades_nullifies_note_notebook_id(client: TestClient) -> None:
    uid = _create_user(client)
    nb_id = _create_notebook(client, uid)
    note_id = _create_note(client, uid)

    # Assign note to notebook
    r = client.put(f"/notes/{note_id}/notebook", json={"notebook_id": nb_id})
    assert r.status_code == 200
    assert r.json()["notebook_id"] == nb_id

    # Delete the notebook
    r = client.delete(f"/notebooks/{nb_id}")
    assert r.status_code == 204

    # Note's notebook_id must be None
    r = client.get(f"/notes/{note_id}")
    assert r.status_code == 200
    assert r.json()["notebook_id"] is None


def test_delete_notebook_removes_it_from_list(client: TestClient) -> None:
    uid = _create_user(client)
    nb_id = _create_notebook(client, uid)
    client.delete(f"/notebooks/{nb_id}")
    r = client.get("/notebooks")
    assert r.status_code == 200
    assert all(nb["id"] != nb_id for nb in r.json())


# ── Notebook Notes ─────────────────────────────────────────────────────────────

def test_list_notebook_notes_not_found_returns_404(client: TestClient) -> None:
    r = client.get("/notebooks/99999/notes")
    assert r.status_code == 404


def test_list_notebook_notes_returns_correct_notes(client: TestClient) -> None:
    uid = _create_user(client)
    nb_id = _create_notebook(client, uid)
    note_id = _create_note(client, uid)

    # Assign note to notebook
    client.put(f"/notes/{note_id}/notebook", json={"notebook_id": nb_id})

    r = client.get(f"/notebooks/{nb_id}/notes")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == note_id


def test_list_notebook_notes_empty_when_no_notes(client: TestClient) -> None:
    uid = _create_user(client)
    nb_id = _create_notebook(client, uid)
    r = client.get(f"/notebooks/{nb_id}/notes")
    assert r.status_code == 200
    assert r.json() == []
