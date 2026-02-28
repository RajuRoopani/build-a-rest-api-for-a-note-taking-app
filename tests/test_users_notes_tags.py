"""
test_users_notes_tags.py — Test suite for Users, Notes, and Tags routers.

Tests cover:
  - Users: create, uniqueness, retrieval, 404 handling
  - Notes: CRUD, filtering, search, pin/archive toggles
  - Tags: add, remove, list, filter by tag
"""

import pytest
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# USERS TESTS (5+ tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestUsers:
    """Test user creation and retrieval."""

    def test_create_user_success(self, client):
        """Create a user and verify 201 response with all fields."""
        res = client.post(
            "/users",
            json={"username": "alice", "email": "alice@example.com"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["id"]  # ID is generated
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
        assert data["created_at"]  # created_at is set

    def test_create_user_duplicate_username(self, client, sample_user):
        """Attempt to create a user with duplicate username → 409 Conflict."""
        res = client.post(
            "/users",
            json={"username": "testuser", "email": "different@example.com"},
        )
        assert res.status_code == 409
        assert "already taken" in res.json()["detail"]

    def test_create_user_case_insensitive_username_uniqueness(self, client, sample_user):
        """Username uniqueness check is case-insensitive → 409."""
        res = client.post(
            "/users",
            json={"username": "TestUser", "email": "uppercase@example.com"},
        )
        assert res.status_code == 409

    def test_get_user_success(self, client, sample_user):
        """Retrieve a user by ID → 200 with correct data."""
        user_id = sample_user["id"]
        res = client.get(f"/users/{user_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == user_id
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_user_not_found(self, client):
        """Attempt to get non-existent user → 404."""
        res = client.get("/users/999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# NOTES TESTS (15+ tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestNotes:
    """Test note CRUD, filtering, search, and toggles."""

    def test_create_note_success(self, client, sample_user):
        """Create a note and verify 201 response with all 10 fields."""
        res = client.post(
            "/notes",
            json={
                "title": "My Note",
                "content": "This is content",
                "user_id": sample_user["id"],
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["id"]
        assert data["title"] == "My Note"
        assert data["content"] == "This is content"
        assert data["user_id"] == sample_user["id"]
        assert data["created_at"]
        assert data["updated_at"]
        assert data["is_pinned"] is False
        assert data["is_archived"] is False
        assert data["tags"] == []
        assert data["notebook_id"] is None

    def test_create_note_nonexistent_user(self, client):
        """Create note with non-existent user_id → 404."""
        res = client.post(
            "/notes",
            json={"title": "Orphan", "content": "No user", "user_id": "999"},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_get_note_success(self, client, sample_note):
        """Retrieve a note by ID → 200."""
        note_id = sample_note["id"]
        res = client.get(f"/notes/{note_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == note_id
        assert data["title"] == sample_note["title"]

    def test_get_note_not_found(self, client):
        """Attempt to get non-existent note → 404."""
        res = client.get("/notes/999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_list_notes_empty(self, client):
        """List notes when none exist → return empty list."""
        res = client.get("/notes")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_notes_all(self, client, sample_user):
        """List all notes → returns all notes."""
        # Create two notes
        client.post("/notes", json={"title": "Note 1", "content": "C1", "user_id": sample_user["id"]})
        client.post("/notes", json={"title": "Note 2", "content": "C2", "user_id": sample_user["id"]})

        res = client.get("/notes")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_list_notes_filtered_by_user_id(self, client):
        """List notes filtered by user_id → returns only that user's notes."""
        # Create two users
        user1 = client.post("/users", json={"username": "u1", "email": "u1@test.com"}).json()
        user2 = client.post("/users", json={"username": "u2", "email": "u2@test.com"}).json()

        # Create notes for both users
        client.post("/notes", json={"title": "U1 Note", "content": "C", "user_id": user1["id"]})
        client.post("/notes", json={"title": "U2 Note", "content": "C", "user_id": user2["id"]})

        res = client.get(f"/notes?user_id={user1['id']}")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["user_id"] == user1["id"]

    def test_list_notes_filtered_by_pinned(self, client, sample_user):
        """List notes filtered by pinned=true → returns only pinned notes."""
        note1 = client.post("/notes", json={"title": "N1", "content": "C", "user_id": sample_user["id"]}).json()
        note2 = client.post("/notes", json={"title": "N2", "content": "C", "user_id": sample_user["id"]}).json()

        # Pin the first note
        client.patch(f"/notes/{note1['id']}/pin")

        res = client.get("/notes?pinned=true")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["id"] == note1["id"]

    def test_list_notes_filtered_by_archived(self, client, sample_user):
        """List notes filtered by archived=true → returns only archived notes."""
        note1 = client.post("/notes", json={"title": "N1", "content": "C", "user_id": sample_user["id"]}).json()
        note2 = client.post("/notes", json={"title": "N2", "content": "C", "user_id": sample_user["id"]}).json()

        # Archive the first note
        client.patch(f"/notes/{note1['id']}/archive")

        res = client.get("/notes?archived=true")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["id"] == note1["id"]

    def test_update_note_title(self, client, sample_note):
        """Update note title → 200, updated_at changes."""
        note_id = sample_note["id"]
        old_updated_at = sample_note["updated_at"]

        # Small sleep to ensure timestamp difference (microseconds matter)
        import time
        time.sleep(0.01)

        res = client.put(f"/notes/{note_id}", json={"title": "New Title"})
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "New Title"
        assert data["updated_at"] != old_updated_at

    def test_update_note_content(self, client, sample_note):
        """Update note content → 200."""
        note_id = sample_note["id"]
        res = client.put(f"/notes/{note_id}", json={"content": "New Content"})
        assert res.status_code == 200
        assert res.json()["content"] == "New Content"

    def test_update_note_not_found(self, client):
        """Update non-existent note → 404."""
        res = client.put("/notes/999", json={"title": "New"})
        assert res.status_code == 404

    def test_delete_note_success(self, client, sample_note):
        """Delete a note → 204."""
        note_id = sample_note["id"]
        res = client.delete(f"/notes/{note_id}")
        assert res.status_code == 204

        # Verify it's gone
        res = client.get(f"/notes/{note_id}")
        assert res.status_code == 404

    def test_delete_note_not_found(self, client):
        """Delete non-existent note → 404."""
        res = client.delete("/notes/999")
        assert res.status_code == 404

    def test_search_notes_by_title(self, client, sample_user):
        """Search notes by title → found."""
        client.post("/notes", json={"title": "Python Guide", "content": "Learn Python", "user_id": sample_user["id"]})
        client.post("/notes", json={"title": "JavaScript Tips", "content": "JS is great", "user_id": sample_user["id"]})

        res = client.get("/notes/search?q=Python")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert "Python" in res.json()[0]["title"]

    def test_search_notes_empty_result(self, client, sample_user):
        """Search notes with no matches → empty list."""
        client.post("/notes", json={"title": "Python Guide", "content": "Learn", "user_id": sample_user["id"]})

        res = client.get("/notes/search?q=nonexistent")
        assert res.status_code == 200
        assert res.json() == []

    def test_pin_toggle_false_to_true_to_false(self, client, sample_note):
        """Pin toggle: false→true→false."""
        note_id = sample_note["id"]

        # Initial state: not pinned
        assert sample_note["is_pinned"] is False

        # Toggle to true
        res = client.patch(f"/notes/{note_id}/pin")
        assert res.status_code == 200
        assert res.json()["is_pinned"] is True

        # Toggle back to false
        res = client.patch(f"/notes/{note_id}/pin")
        assert res.status_code == 200
        assert res.json()["is_pinned"] is False

    def test_archive_toggle_false_to_true_to_false(self, client, sample_note):
        """Archive toggle: false→true→false."""
        note_id = sample_note["id"]

        # Initial state: not archived
        assert sample_note["is_archived"] is False

        # Toggle to true
        res = client.patch(f"/notes/{note_id}/archive")
        assert res.status_code == 200
        assert res.json()["is_archived"] is True

        # Toggle back to false
        res = client.patch(f"/notes/{note_id}/archive")
        assert res.status_code == 200
        assert res.json()["is_archived"] is False


# ══════════════════════════════════════════════════════════════════════════════
# TAGS TESTS (8+ tests)
# ══════════════════════════════════════════════════════════════════════════════


class TestTags:
    """Test tag operations: add, remove, list, filter."""

    def test_add_tag_success(self, client, sample_note):
        """Add a tag to a note → tag appears in note.tags."""
        note_id = sample_note["id"]
        res = client.post(f"/notes/{note_id}/tags", json={"label": "urgent"})
        assert res.status_code == 200
        assert "urgent" in res.json()["tags"]

    def test_add_tag_duplicate_idempotent(self, client, sample_note):
        """Add duplicate tag → idempotent, no duplicate."""
        note_id = sample_note["id"]
        # Add tag once
        client.post(f"/notes/{note_id}/tags", json={"label": "work"})
        # Add again
        res = client.post(f"/notes/{note_id}/tags", json={"label": "work"})
        assert res.status_code == 200
        tags = res.json()["tags"]
        assert tags.count("work") == 1

    def test_remove_tag_success(self, client, sample_note):
        """Remove a tag from a note → tag removed."""
        note_id = sample_note["id"]
        # Add tag
        client.post(f"/notes/{note_id}/tags", json={"label": "important"})
        # Remove tag
        res = client.delete(f"/notes/{note_id}/tags/important")
        assert res.status_code == 200
        assert "important" not in res.json()["tags"]

    def test_remove_tag_not_found(self, client, sample_note):
        """Remove non-existent tag → 404."""
        note_id = sample_note["id"]
        res = client.delete(f"/notes/{note_id}/tags/nonexistent")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_list_all_tags_sorted(self, client, sample_user):
        """List all tags → returns sorted list of unique tags."""
        # Create notes with various tags
        note1 = client.post(
            "/notes", json={"title": "N1", "content": "C", "user_id": sample_user["id"]}
        ).json()
        note2 = client.post(
            "/notes", json={"title": "N2", "content": "C", "user_id": sample_user["id"]}
        ).json()

        # Add tags in non-alphabetical order
        client.post(f"/notes/{note1['id']}/tags", json={"label": "zebra"})
        client.post(f"/notes/{note1['id']}/tags", json={"label": "apple"})
        client.post(f"/notes/{note2['id']}/tags", json={"label": "banana"})

        res = client.get("/tags")
        assert res.status_code == 200
        tags = res.json()
        assert tags == ["apple", "banana", "zebra"]  # Sorted

    def test_list_notes_by_tag_matching(self, client, sample_user):
        """List notes by tag → returns matching notes."""
        note1 = client.post(
            "/notes", json={"title": "N1", "content": "C", "user_id": sample_user["id"]}
        ).json()
        note2 = client.post(
            "/notes", json={"title": "N2", "content": "C", "user_id": sample_user["id"]}
        ).json()

        # Add 'project' tag to note1 only
        client.post(f"/notes/{note1['id']}/tags", json={"label": "project"})

        res = client.get("/tags/project/notes")
        assert res.status_code == 200
        notes = res.json()
        assert len(notes) == 1
        assert notes[0]["id"] == note1["id"]

    def test_list_notes_by_tag_empty(self, client, sample_user):
        """List notes by tag with no matches → empty list."""
        client.post("/notes", json={"title": "N1", "content": "C", "user_id": sample_user["id"]})

        res = client.get("/tags/nonexistent/notes")
        assert res.status_code == 200
        assert res.json() == []
