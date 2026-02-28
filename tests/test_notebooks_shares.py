"""
test_notebooks_shares.py — Comprehensive tests for Notebooks and Shares routers.

Tests cover:
- Notebook CRUD operations and cascading deletes
- Share operations and idempotency
- Error cases (404, 422)
"""

import pytest
from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES — Sample data creators
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_user(client: TestClient) -> dict:
    """Create and return a sample user."""
    res = client.post(
        "/users",
        json={"username": "testuser", "email": "test@example.com"},
    )
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def second_user(client: TestClient) -> dict:
    """Create and return a second sample user."""
    res = client.post(
        "/users",
        json={"username": "testuser2", "email": "test2@example.com"},
    )
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def sample_note(client: TestClient, sample_user: dict) -> dict:
    """Create and return a sample note."""
    res = client.post(
        "/notes",
        json={
            "title": "Test Note",
            "content": "Test content",
            "user_id": sample_user["id"],
        },
    )
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def sample_notebook(client: TestClient, sample_user: dict) -> dict:
    """Create and return a sample notebook."""
    res = client.post(
        "/notebooks",
        json={"name": "My Notebook", "user_id": sample_user["id"]},
    )
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def second_notebook(client: TestClient, sample_user: dict) -> dict:
    """Create and return a second sample notebook."""
    res = client.post(
        "/notebooks",
        json={"name": "Another Notebook", "user_id": sample_user["id"]},
    )
    assert res.status_code == 201
    return res.json()


# ══════════════════════════════════════════════════════════════════════════════
# NOTEBOOKS TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestNotebooksCreate:
    """Tests for POST /notebooks (create notebook)."""

    def test_create_notebook_returns_201(
        self, client: TestClient, sample_user: dict
    ) -> None:
        """Notebook creation should return 201 with id, name, user_id, created_at."""
        res = client.post(
            "/notebooks",
            json={"name": "My First Notebook", "user_id": sample_user["id"]},
        )
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["name"] == "My First Notebook"
        assert data["user_id"] == sample_user["id"]
        assert "created_at" in data

    def test_create_notebook_with_nonexistent_user_returns_404(
        self, client: TestClient
    ) -> None:
        """Creating a notebook with a non-existent user should return 404."""
        res = client.post(
            "/notebooks",
            json={"name": "Orphan Notebook", "user_id": "999"},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_create_multiple_notebooks_for_same_user(
        self, client: TestClient, sample_user: dict
    ) -> None:
        """User should be able to create multiple notebooks."""
        nb1 = client.post(
            "/notebooks",
            json={"name": "Notebook 1", "user_id": sample_user["id"]},
        ).json()
        nb2 = client.post(
            "/notebooks",
            json={"name": "Notebook 2", "user_id": sample_user["id"]},
        ).json()
        assert nb1["id"] != nb2["id"]
        assert nb1["name"] == "Notebook 1"
        assert nb2["name"] == "Notebook 2"


class TestNotebooksList:
    """Tests for GET /notebooks (list notebooks)."""

    def test_list_notebooks_empty_returns_empty_list(
        self, client: TestClient
    ) -> None:
        """List notebooks with no notebooks should return empty list."""
        res = client.get("/notebooks")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_notebooks_returns_all_notebooks(
        self, client: TestClient, sample_user: dict, second_user: dict
    ) -> None:
        """List notebooks should return all notebooks for all users."""
        nb1 = client.post(
            "/notebooks",
            json={"name": "NB1", "user_id": sample_user["id"]},
        ).json()
        nb2 = client.post(
            "/notebooks",
            json={"name": "NB2", "user_id": second_user["id"]},
        ).json()

        res = client.get("/notebooks")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        ids = {nb["id"] for nb in data}
        assert nb1["id"] in ids
        assert nb2["id"] in ids

    def test_list_notebooks_filtered_by_user_id(
        self, client: TestClient, sample_user: dict, second_user: dict
    ) -> None:
        """List notebooks with user_id filter should return only that user's notebooks."""
        nb1 = client.post(
            "/notebooks",
            json={"name": "User1 NB", "user_id": sample_user["id"]},
        ).json()
        client.post(
            "/notebooks",
            json={"name": "User2 NB", "user_id": second_user["id"]},
        )

        res = client.get(f"/notebooks?user_id={sample_user['id']}")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == nb1["id"]
        assert data[0]["user_id"] == sample_user["id"]


class TestNotebooksGet:
    """Tests for GET /notebooks/{notebook_id} (get single notebook)."""

    def test_get_notebook_by_id_returns_200(
        self, client: TestClient, sample_notebook: dict
    ) -> None:
        """Getting an existing notebook should return 200 with full details."""
        res = client.get(f"/notebooks/{sample_notebook['id']}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == sample_notebook["id"]
        assert data["name"] == sample_notebook["name"]
        assert data["user_id"] == sample_notebook["user_id"]

    def test_get_nonexistent_notebook_returns_404(self, client: TestClient) -> None:
        """Getting a non-existent notebook should return 404."""
        res = client.get("/notebooks/999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


class TestNotebooksDelete:
    """Tests for DELETE /notebooks/{notebook_id} (delete notebook)."""

    def test_delete_notebook_returns_204(
        self, client: TestClient, sample_notebook: dict
    ) -> None:
        """Deleting an existing notebook should return 204 (no content)."""
        res = client.delete(f"/notebooks/{sample_notebook['id']}")
        assert res.status_code == 204

        # Verify it's gone
        res_check = client.get(f"/notebooks/{sample_notebook['id']}")
        assert res_check.status_code == 404

    def test_delete_nonexistent_notebook_returns_404(self, client: TestClient) -> None:
        """Deleting a non-existent notebook should return 404."""
        res = client.delete("/notebooks/999")
        assert res.status_code == 404

    def test_delete_notebook_cascades_note_notebook_id_to_none(
        self,
        client: TestClient,
        sample_user: dict,
        sample_notebook: dict,
    ) -> None:
        """Deleting a notebook should nullify notebook_id on its notes."""
        # Create a note assigned to the notebook
        note = client.post(
            "/notes",
            json={
                "title": "Note in Notebook",
                "content": "Content",
                "user_id": sample_user["id"],
            },
        ).json()

        # Assign note to notebook
        res_assign = client.put(
            f"/notes/{note['id']}/notebook",
            json={"notebook_id": sample_notebook["id"]},
        )
        assert res_assign.status_code == 200
        note_before = res_assign.json()
        assert note_before["notebook_id"] == sample_notebook["id"]

        # Delete the notebook
        res_delete = client.delete(f"/notebooks/{sample_notebook['id']}")
        assert res_delete.status_code == 204

        # Check that the note's notebook_id is now None
        res_check = client.get(f"/notes/{note['id']}")
        assert res_check.status_code == 200
        note_after = res_check.json()
        assert note_after["notebook_id"] is None


class TestNotebookNotes:
    """Tests for GET /notebooks/{notebook_id}/notes (list notes in notebook)."""

    def test_list_notes_in_notebook_returns_notes(
        self,
        client: TestClient,
        sample_user: dict,
        sample_notebook: dict,
    ) -> None:
        """List notes in a notebook should return notes assigned to it."""
        # Create notes
        note1 = client.post(
            "/notes",
            json={
                "title": "Note 1",
                "content": "Content 1",
                "user_id": sample_user["id"],
            },
        ).json()
        note2 = client.post(
            "/notes",
            json={
                "title": "Note 2",
                "content": "Content 2",
                "user_id": sample_user["id"],
            },
        ).json()

        # Assign both to notebook
        client.put(
            f"/notes/{note1['id']}/notebook",
            json={"notebook_id": sample_notebook["id"]},
        )
        client.put(
            f"/notes/{note2['id']}/notebook",
            json={"notebook_id": sample_notebook["id"]},
        )

        # List notes in notebook
        res = client.get(f"/notebooks/{sample_notebook['id']}/notes")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        ids = {note["id"] for note in data}
        assert note1["id"] in ids
        assert note2["id"] in ids

    def test_list_notes_in_notebook_returns_empty_list_when_no_notes(
        self, client: TestClient, sample_notebook: dict
    ) -> None:
        """List notes in an empty notebook should return empty list."""
        res = client.get(f"/notebooks/{sample_notebook['id']}/notes")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_notes_in_nonexistent_notebook_returns_404(
        self, client: TestClient
    ) -> None:
        """List notes in a non-existent notebook should return 404."""
        res = client.get("/notebooks/999/notes")
        assert res.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# SHARES TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestSharesCreate:
    """Tests for POST /notes/{note_id}/share (share note with user)."""

    def test_share_note_with_user_returns_200(
        self,
        client: TestClient,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """Sharing a note with a user should return 200 with share details."""
        res = client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["note_id"] == sample_note["id"]
        assert data["user_id"] == second_user["id"]
        assert "shared_at" in data

    def test_share_note_with_nonexistent_user_returns_404(
        self, client: TestClient, sample_note: dict
    ) -> None:
        """Sharing with a non-existent user should return 404."""
        res = client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": "999"},
        )
        assert res.status_code == 404

    def test_share_nonexistent_note_returns_404(
        self, client: TestClient, second_user: dict
    ) -> None:
        """Sharing a non-existent note should return 404."""
        res = client.post(
            "/notes/999/share",
            json={"user_id": second_user["id"]},
        )
        assert res.status_code == 404

    def test_share_is_idempotent(
        self,
        client: TestClient,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """Sharing the same note with the same user twice should return the same record."""
        res1 = client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )
        assert res1.status_code == 200
        share1 = res1.json()

        res2 = client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )
        assert res2.status_code == 200
        share2 = res2.json()

        # Should return the exact same share record (idempotent)
        assert share1["note_id"] == share2["note_id"]
        assert share1["user_id"] == share2["user_id"]
        assert share1["shared_at"] == share2["shared_at"]


class TestSharesList:
    """Tests for GET /notes/{note_id}/shares (list shares for a note)."""

    def test_list_note_shares_returns_shares(
        self,
        client: TestClient,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """List shares for a note should return all shares."""
        # Share with a user
        client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )

        res = client.get(f"/notes/{sample_note['id']}/shares")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["note_id"] == sample_note["id"]
        assert data[0]["user_id"] == second_user["id"]

    def test_list_note_shares_multiple_users(
        self,
        client: TestClient,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """List shares should return all users a note is shared with."""
        # Create third user
        user3 = client.post(
            "/users",
            json={"username": "testuser3", "email": "test3@example.com"},
        ).json()

        # Share with two users
        client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )
        client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": user3["id"]},
        )

        res = client.get(f"/notes/{sample_note['id']}/shares")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        user_ids = {s["user_id"] for s in data}
        assert second_user["id"] in user_ids
        assert user3["id"] in user_ids

    def test_list_note_shares_nonexistent_note_returns_404(
        self, client: TestClient
    ) -> None:
        """List shares for non-existent note should return 404."""
        res = client.get("/notes/999/shares")
        assert res.status_code == 404

    def test_list_note_shares_empty_returns_empty_list(
        self, client: TestClient, sample_note: dict
    ) -> None:
        """List shares for a note with no shares should return empty list."""
        res = client.get(f"/notes/{sample_note['id']}/shares")
        assert res.status_code == 200
        assert res.json() == []


class TestSharesDelete:
    """Tests for DELETE /notes/{note_id}/share/{user_id} (unshare note)."""

    def test_unshare_note_returns_200(
        self,
        client: TestClient,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """Unsharing a note should return 200."""
        # First share
        client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )

        # Then unshare
        res = client.delete(
            f"/notes/{sample_note['id']}/share/{second_user['id']}"
        )
        assert res.status_code == 200

        # Verify it's gone
        res_check = client.get(f"/notes/{sample_note['id']}/shares")
        assert res_check.status_code == 200
        assert res_check.json() == []

    def test_unshare_nonexistent_share_returns_404(
        self,
        client: TestClient,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """Unsharing when no share exists should return 404."""
        res = client.delete(
            f"/notes/{sample_note['id']}/share/{second_user['id']}"
        )
        assert res.status_code == 404

    def test_unshare_nonexistent_note_returns_404(
        self, client: TestClient, second_user: dict
    ) -> None:
        """Unsharing from non-existent note should return 404."""
        res = client.delete(
            f"/notes/999/share/{second_user['id']}"
        )
        assert res.status_code == 404


class TestNotesSharedWith:
    """Tests for GET /users/{user_id}/shared (list notes shared with a user)."""

    def test_list_notes_shared_with_user_returns_notes(
        self,
        client: TestClient,
        sample_user: dict,
        sample_note: dict,
        second_user: dict,
    ) -> None:
        """List notes shared with a user should return notes shared with them."""
        # Share note with second_user
        client.post(
            f"/notes/{sample_note['id']}/share",
            json={"user_id": second_user["id"]},
        )

        res = client.get(f"/users/{second_user['id']}/shared")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_note["id"]

    def test_list_notes_shared_with_user_multiple_notes(
        self,
        client: TestClient,
        sample_user: dict,
        second_user: dict,
    ) -> None:
        """List shared notes should return multiple notes if shared."""
        # Create two notes
        note1 = client.post(
            "/notes",
            json={
                "title": "Note 1",
                "content": "Content 1",
                "user_id": sample_user["id"],
            },
        ).json()
        note2 = client.post(
            "/notes",
            json={
                "title": "Note 2",
                "content": "Content 2",
                "user_id": sample_user["id"],
            },
        ).json()

        # Share both with second_user
        client.post(
            f"/notes/{note1['id']}/share",
            json={"user_id": second_user["id"]},
        )
        client.post(
            f"/notes/{note2['id']}/share",
            json={"user_id": second_user["id"]},
        )

        res = client.get(f"/users/{second_user['id']}/shared")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        ids = {n["id"] for n in data}
        assert note1["id"] in ids
        assert note2["id"] in ids

    def test_list_notes_shared_with_user_returns_empty_when_nothing_shared(
        self, client: TestClient, second_user: dict
    ) -> None:
        """List shared notes for user with no shares should return empty list."""
        res = client.get(f"/users/{second_user['id']}/shared")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_notes_shared_with_nonexistent_user_returns_404(
        self, client: TestClient
    ) -> None:
        """List shared notes for non-existent user should return 404."""
        res = client.get("/users/999/shared")
        assert res.status_code == 404


class TestSharesCascade:
    """Tests for cascading deletes when notes or users are deleted."""

    def test_delete_note_removes_share_records(
        self,
        client: TestClient,
        sample_user: dict,
        second_user: dict,
    ) -> None:
        """Deleting a note should remove its share records."""
        # Create and share a note
        note = client.post(
            "/notes",
            json={
                "title": "To Delete",
                "content": "Will be deleted",
                "user_id": sample_user["id"],
            },
        ).json()

        client.post(
            f"/notes/{note['id']}/share",
            json={"user_id": second_user["id"]},
        )

        # Verify share exists
        res_shares = client.get(f"/notes/{note['id']}/shares")
        assert len(res_shares.json()) == 1

        # Delete the note
        res_delete = client.delete(f"/notes/{note['id']}")
        assert res_delete.status_code == 204

        # Verify the share is also gone (note doesn't exist, so listing shares returns 404)
        res_check = client.get(f"/notes/{note['id']}/shares")
        assert res_check.status_code == 404

        # Also verify the note is not in the shared list for the other user
        res_shared_with = client.get(f"/users/{second_user['id']}/shared")
        assert res_shared_with.status_code == 200
        assert len(res_shared_with.json()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_complete_notebook_workflow(
        self,
        client: TestClient,
        sample_user: dict,
    ) -> None:
        """Test a complete workflow: create notebook, add notes, delete."""
        # Create notebook
        nb = client.post(
            "/notebooks",
            json={"name": "Project Notes", "user_id": sample_user["id"]},
        ).json()

        # Create notes
        note1 = client.post(
            "/notes",
            json={
                "title": "Design",
                "content": "UI mockups",
                "user_id": sample_user["id"],
            },
        ).json()
        note2 = client.post(
            "/notes",
            json={
                "title": "Implementation",
                "content": "Code structure",
                "user_id": sample_user["id"],
            },
        ).json()

        # Assign notes to notebook
        client.put(
            f"/notes/{note1['id']}/notebook",
            json={"notebook_id": nb["id"]},
        )
        client.put(
            f"/notes/{note2['id']}/notebook",
            json={"notebook_id": nb["id"]},
        )

        # Verify notes are in notebook
        res_notes = client.get(f"/notebooks/{nb['id']}/notes")
        assert len(res_notes.json()) == 2

        # Delete notebook
        res_delete = client.delete(f"/notebooks/{nb['id']}")
        assert res_delete.status_code == 204

        # Verify notes still exist but notebook_id is None
        res_note1 = client.get(f"/notes/{note1['id']}")
        assert res_note1.json()["notebook_id"] is None

    def test_complete_sharing_workflow(
        self,
        client: TestClient,
        sample_user: dict,
    ) -> None:
        """Test a complete workflow: share notes, list shares, unshare."""
        # Create users and notes
        user2 = client.post(
            "/users",
            json={"username": "user2", "email": "user2@example.com"},
        ).json()
        user3 = client.post(
            "/users",
            json={"username": "user3", "email": "user3@example.com"},
        ).json()

        note = client.post(
            "/notes",
            json={
                "title": "Shared Note",
                "content": "To be shared",
                "user_id": sample_user["id"],
            },
        ).json()

        # Share with multiple users
        client.post(
            f"/notes/{note['id']}/share",
            json={"user_id": user2["id"]},
        )
        client.post(
            f"/notes/{note['id']}/share",
            json={"user_id": user3["id"]},
        )

        # Verify shares
        res_shares = client.get(f"/notes/{note['id']}/shares")
        assert len(res_shares.json()) == 2

        res_user2_shared = client.get(f"/users/{user2['id']}/shared")
        assert len(res_user2_shared.json()) == 1

        res_user3_shared = client.get(f"/users/{user3['id']}/shared")
        assert len(res_user3_shared.json()) == 1

        # Unshare with user2
        client.delete(f"/notes/{note['id']}/share/{user2['id']}")

        # Verify user2 no longer has the share
        res_user2_shared_after = client.get(f"/users/{user2['id']}/shared")
        assert len(res_user2_shared_after.json()) == 0

        # Verify user3 still has it
        res_user3_shared_after = client.get(f"/users/{user3['id']}/shared")
        assert len(res_user3_shared_after.json()) == 1

        # Verify note still has only one share
        res_shares_after = client.get(f"/notes/{note['id']}/shares")
        assert len(res_shares_after.json()) == 1
        assert res_shares_after.json()[0]["user_id"] == user3["id"]
