"""
conftest.py — pytest fixtures for the Note-Taking API test suite.

Provides:
- clean_storage: autouse fixture that resets storage between tests
- client: TestClient for making HTTP requests to the app
"""

import pytest
from fastapi.testclient import TestClient

from notes_app.main import app
from notes_app.storage import reset_storage


@pytest.fixture(autouse=True)
def clean_storage():
    """Reset all storage before and after each test."""
    reset_storage()
    yield
    reset_storage()


@pytest.fixture
def client():
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_user(client):
    """Create and return a sample user."""
    res = client.post("/users", json={"username": "testuser", "email": "test@example.com"})
    return res.json()


@pytest.fixture
def sample_note(client, sample_user):
    """Create and return a sample note."""
    res = client.post(
        "/notes",
        json={"title": "Test Note", "content": "Test content", "user_id": sample_user["id"]},
    )
    return res.json()
