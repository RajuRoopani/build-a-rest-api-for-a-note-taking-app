# Note-Taking REST API

A full-featured REST API for creating, organising, searching, and sharing
notes. Built with **FastAPI** and **in-memory storage** — no database required.
Ships with a single-page HTML frontend, interactive API docs, and 92 tests.

---

## Table of Contents

1. [Features](#features)
2. [Quick Start](#quick-start)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [API Reference](#api-reference)
   - [Users](#users)
   - [Notes](#notes)
   - [Tags](#tags)
   - [Notebooks](#notebooks)
   - [Shares](#shares)
   - [Meta](#meta)
6. [Data Models](#data-models)
7. [Frontend](#frontend)
8. [Testing](#testing)
9. [Design Decisions](#design-decisions)

---

## Features

- **Users** — Create users with unique, case-insensitive usernames
- **Notes** — Full CRUD: create, read, update, delete, with auto-timestamps
- **Search** — Case-insensitive substring search across note titles and content
- **Pin / Archive** — Toggle boolean flags on notes via PATCH endpoints
- **Tags** — Add/remove string tags on notes, list all tags, filter notes by tag
- **Notebooks** — Group notes into named notebooks; deletion nullifies references
- **Sharing** — Share notes with other users (idempotent); view and revoke shares
- **Filters** — Query notes by `user_id`, `pinned`, and `archived` status
- **Health check** — Liveness probe at `GET /health`
- **Frontend** — Zero-build-step single-page HTML UI served at `GET /`
- **Interactive docs** — Swagger UI at `GET /docs`, ReDoc at `GET /redoc`

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd notes_app

# 2. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the development server
uvicorn notes_app.main:app --reload

# The server is now running at http://localhost:8000
#   Frontend:       http://localhost:8000/
#   Swagger docs:   http://localhost:8000/docs
#   ReDoc:          http://localhost:8000/redoc
#   Health check:   http://localhost:8000/health
```

> **Note:** Data is held in memory. It resets every time the server restarts.

---

## Tech Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) | Async routing, dependency injection, OpenAPI spec generation |
| Data validation | [Pydantic v2](https://docs.pydantic.dev/) | Request body parsing and response serialisation |
| ASGI server | [Uvicorn](https://www.uvicorn.org/) | High-performance async server with `--reload` dev mode |
| Templating | [Jinja2](https://jinja.palletsprojects.com/) | Server-side rendering of the frontend HTML page |
| Email validation | [email-validator](https://pypi.org/project/email-validator/) | Pydantic `EmailStr` support in `UserCreate` |
| HTTP client (tests) | [httpx](https://www.python-httpx.org/) | `TestClient` used by pytest via Starlette |
| Test runner | [pytest](https://pytest.org/) | Collects and runs all 92 tests |

---

## Project Structure

```
notes_app/
├── main.py                     # FastAPI app, router registration, health + frontend routes
├── models.py                   # Pydantic request/response models (UserCreate, NoteOut, …)
├── storage.py                  # In-memory data store; reset_storage() for tests
├── requirements.txt            # Pinned Python dependencies
├── __init__.py
│
├── routers/
│   ├── __init__.py
│   ├── users.py                # POST /users  GET /users/{id}  (2 endpoints)
│   ├── notes.py                # Full note CRUD + search + toggles + notebook assign (9 endpoints)
│   ├── tags.py                 # Tag add/remove + global listing + filter by tag (4 endpoints)
│   ├── notebooks.py            # Notebook CRUD + list notes in notebook (5 endpoints)
│   └── shares.py               # Share/unshare notes + view shared notes (4 endpoints)
│
├── templates/
│   └── index.html              # Single-page frontend (vanilla HTML/CSS/JS, no build step)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared pytest fixtures: TestClient + storage reset
│   ├── test_users_notes_tags.py    # 30 tests — users, notes, tags
│   ├── test_notebooks.py           # 14 tests — notebooks
│   ├── test_shares.py              # 16 tests — shares
│   └── test_notebooks_shares.py    # 32 tests — notebooks + shares integration
│
├── designs/
│   └── frontend-ux.md          # UX specification written by UX engineer
│
└── docs/
    ├── notes-api-design.md     # Full architecture and API contracts document
    └── adr/
        ├── ADR-001-in-memory-storage.md   # Why no database
        └── ADR-002-route-ordering.md      # Why /search must precede /{note_id}
```

---

## API Reference

All endpoints consume and return **JSON**. Timestamps are ISO-8601 strings in
UTC (e.g. `"2024-06-01T12:00:00Z"`). IDs are numeric strings (`"1"`, `"2"`, …).

### Users

#### `POST /users` — Create a user

**Request body**

```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```

**Response `201 Created`**

```json
{
  "id": "1",
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2024-06-01T12:00:00Z"
}
```

| Status | Condition |
|--------|-----------|
| 201 | User created successfully |
| 409 | Username already taken (case-insensitive) |

---

#### `GET /users/{user_id}` — Get a user

**Path parameter:** `user_id` — string ID of the user

**Response `200 OK`**

```json
{
  "id": "1",
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2024-06-01T12:00:00Z"
}
```

| Status | Condition |
|--------|-----------|
| 200 | User found |
| 404 | User not found |

---

### Notes

#### `POST /notes` — Create a note

**Request body**

```json
{
  "title": "Meeting notes",
  "content": "Discuss Q3 roadmap.",
  "user_id": "1"
}
```

**Response `201 Created`**

```json
{
  "id": "1",
  "title": "Meeting notes",
  "content": "Discuss Q3 roadmap.",
  "user_id": "1",
  "created_at": "2024-06-01T12:00:00Z",
  "updated_at": "2024-06-01T12:00:00Z",
  "is_pinned": false,
  "is_archived": false,
  "tags": [],
  "notebook_id": null
}
```

| Status | Condition |
|--------|-----------|
| 201 | Note created |
| 404 | `user_id` does not reference an existing user |

---

#### `GET /notes/search` — Search notes

> ⚠️ This route is **declared before** `GET /notes/{note_id}` in the router to
> prevent FastAPI treating the literal string `"search"` as a path parameter.

**Query parameter:** `q` (required) — case-insensitive substring to match
against note `title` and `content`.

**Example:** `GET /notes/search?q=roadmap`

**Response `200 OK`** — always a list, empty when no matches

```json
[
  {
    "id": "1",
    "title": "Meeting notes",
    "content": "Discuss Q3 roadmap.",
    ...
  }
]
```

| Status | Condition |
|--------|-----------|
| 200 | Always (empty list when no matches) |

---

#### `GET /notes/{note_id}` — Get a note

**Response `200 OK`** — single `NoteOut` object (see schema above).

| Status | Condition |
|--------|-----------|
| 200 | Note found |
| 404 | Note not found |

---

#### `GET /notes` — List notes

Optional query parameters for filtering (all combinable with AND logic):

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | Return only notes owned by this user |
| `pinned` | boolean | `true` = pinned only, `false` = unpinned only |
| `archived` | boolean | `true` = archived only, `false` = active only |

**Example:** `GET /notes?user_id=1&pinned=true`

**Response `200 OK`** — list of `NoteOut` objects (empty list when no matches).

---

#### `PUT /notes/{note_id}` — Update a note

Both fields are optional — supply only the fields you want to change.
`updated_at` is refreshed on every call.

**Request body**

```json
{
  "title": "Updated title",
  "content": "Updated content."
}
```

**Response `200 OK`** — updated `NoteOut`.

| Status | Condition |
|--------|-----------|
| 200 | Note updated |
| 404 | Note not found |

---

#### `DELETE /notes/{note_id}` — Delete a note

Also removes all share records referencing this note.

**Response `204 No Content`** — empty body.

| Status | Condition |
|--------|-----------|
| 204 | Note deleted |
| 404 | Note not found |

---

#### `PATCH /notes/{note_id}/pin` — Toggle pin

Flips `is_pinned` from `false → true` or `true → false`. Updates `updated_at`.

**Response `200 OK`** — updated `NoteOut`.

| Status | Condition |
|--------|-----------|
| 200 | Pin toggled |
| 404 | Note not found |

---

#### `PATCH /notes/{note_id}/archive` — Toggle archive

Flips `is_archived` from `false → true` or `true → false`. Updates `updated_at`.

**Response `200 OK`** — updated `NoteOut`.

| Status | Condition |
|--------|-----------|
| 200 | Archive toggled |
| 404 | Note not found |

---

#### `PUT /notes/{note_id}/notebook` — Assign to notebook

**Request body**

```json
{
  "notebook_id": "2"
}
```

**Response `200 OK`** — updated `NoteOut` with `notebook_id` set.

| Status | Condition |
|--------|-----------|
| 200 | Notebook assigned |
| 404 | Note or notebook not found |

---

### Tags

#### `POST /notes/{note_id}/tags` — Add a tag

Adding a tag that already exists on the note is a **no-op** (idempotent).
Leading/trailing whitespace is stripped from the label.

**Request body**

```json
{
  "label": "work"
}
```

**Response `200 OK`** — updated `NoteOut` with the new tag in `tags`.

| Status | Condition |
|--------|-----------|
| 200 | Tag added (or already present) |
| 404 | Note not found |

---

#### `DELETE /notes/{note_id}/tags/{tag}` — Remove a tag

**Path parameter:** `tag` — exact tag string to remove.

**Response `200 OK`** — updated `NoteOut` with the tag removed from `tags`.

| Status | Condition |
|--------|-----------|
| 200 | Tag removed |
| 404 | Note not found, or tag not present on the note |

---

#### `GET /tags` — List all tags

Returns a **deduplicated, alphabetically sorted** list of every tag across all
notes.

**Response `200 OK`**

```json
["design", "urgent", "work"]
```

---

#### `GET /tags/{tag}/notes` — Notes with a tag

Returns all notes that contain the given tag (exact string match).
Returns an empty list if no notes have that tag.

**Response `200 OK`** — list of `NoteOut` objects.

---

### Notebooks

#### `POST /notebooks` — Create a notebook

**Request body**

```json
{
  "name": "Work Projects",
  "user_id": "1"
}
```

**Response `201 Created`**

```json
{
  "id": "1",
  "name": "Work Projects",
  "user_id": "1",
  "created_at": "2024-06-01T12:00:00Z"
}
```

| Status | Condition |
|--------|-----------|
| 201 | Notebook created |
| 404 | `user_id` does not reference an existing user |

---

#### `GET /notebooks` — List notebooks

**Query parameter:** `user_id` (optional) — filter notebooks by owner.

**Response `200 OK`** — list of `NotebookOut` objects.

---

#### `GET /notebooks/{notebook_id}` — Get a notebook

**Response `200 OK`** — single `NotebookOut`.

| Status | Condition |
|--------|-----------|
| 200 | Notebook found |
| 404 | Notebook not found |

---

#### `DELETE /notebooks/{notebook_id}` — Delete a notebook

**Cascade behaviour:** all notes whose `notebook_id` matched the deleted
notebook have their `notebook_id` set to `null`. The notes themselves are
**not** deleted.

**Response `204 No Content`** — empty body.

| Status | Condition |
|--------|-----------|
| 204 | Notebook deleted |
| 404 | Notebook not found |

---

#### `GET /notebooks/{notebook_id}/notes` — Notes in a notebook

**Response `200 OK`** — list of `NoteOut` objects assigned to this notebook.
Returns an empty list if the notebook exists but has no notes.

| Status | Condition |
|--------|-----------|
| 200 | Notebook found (list may be empty) |
| 404 | Notebook not found |

---

### Shares

#### `POST /notes/{note_id}/share` — Share a note

Sharing the same note with the same user a second time is **idempotent** — the
existing share record is returned without creating a duplicate.

**Request body**

```json
{
  "user_id": "2"
}
```

**Response `200 OK`**

```json
{
  "note_id": "1",
  "user_id": "2",
  "shared_at": "2024-06-01T13:00:00Z"
}
```

| Status | Condition |
|--------|-----------|
| 200 | Note shared (or already shared) |
| 404 | Note or target user not found |

---

#### `GET /notes/{note_id}/shares` — List shares for a note

**Response `200 OK`** — list of `ShareOut` objects. Empty list if the note has
not been shared with anyone.

| Status | Condition |
|--------|-----------|
| 200 | Note found (list may be empty) |
| 404 | Note not found |

---

#### `DELETE /notes/{note_id}/share/{user_id}` — Unshare a note

**Response `200 OK`**

```json
{
  "detail": "Note '1' unshared from user '2'."
}
```

| Status | Condition |
|--------|-----------|
| 200 | Share record removed |
| 404 | Note, user, or share record not found |

---

#### `GET /users/{user_id}/shared` — Notes shared with a user

**Response `200 OK`** — list of `NoteOut` objects for every note shared with
this user. Empty list if nothing has been shared with them.

| Status | Condition |
|--------|-----------|
| 200 | User found (list may be empty) |
| 404 | User not found |

---

### Meta

#### `GET /health` — Health check

**Response `200 OK`**

```json
{
  "status": "ok"
}
```

---

## Data Models

### User

```json
{
  "id": "1",
  "username": "alice",
  "email": "alice@example.com",
  "created_at": "2024-06-01T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-incrementing numeric string |
| `username` | string | Unique (case-insensitive) |
| `email` | string | Valid email format required |
| `created_at` | datetime | UTC timestamp set at creation |

---

### Note

```json
{
  "id": "1",
  "title": "Meeting notes",
  "content": "Discuss Q3 roadmap.",
  "user_id": "1",
  "created_at": "2024-06-01T12:00:00Z",
  "updated_at": "2024-06-01T14:30:00Z",
  "is_pinned": false,
  "is_archived": false,
  "tags": ["work", "q3"],
  "notebook_id": "2"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-incrementing numeric string |
| `title` | string | Note title |
| `content` | string | Note body text |
| `user_id` | string | ID of the owning user |
| `created_at` | datetime | UTC timestamp set at creation |
| `updated_at` | datetime | UTC timestamp updated on every mutation |
| `is_pinned` | boolean | `true` if the note is pinned |
| `is_archived` | boolean | `true` if the note is archived |
| `tags` | array of strings | Ordered list of tag labels |
| `notebook_id` | string or null | ID of the assigned notebook, or `null` |

---

### Notebook

```json
{
  "id": "1",
  "name": "Work Projects",
  "user_id": "1",
  "created_at": "2024-06-01T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-incrementing numeric string |
| `name` | string | Notebook display name |
| `user_id` | string | ID of the owning user |
| `created_at` | datetime | UTC timestamp set at creation |

---

### Share

```json
{
  "note_id": "1",
  "user_id": "2",
  "shared_at": "2024-06-01T13:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `note_id` | string | ID of the shared note |
| `user_id` | string | ID of the user the note is shared with |
| `shared_at` | datetime | UTC timestamp when the share was first created |

---

## Frontend

The app ships a zero-build-step single-page HTML frontend at `GET /`. It is
rendered server-side via **Jinja2** from `templates/index.html` and then
communicates with the REST API entirely through client-side JavaScript.

### Frontend capabilities

- **Create notes** — form to enter title and content for a selected user
- **List notes** — shows all notes with their pin/archive status and tags
- **Search** — real-time substring search using `GET /notes/search?q=`
- **Pin / Archive toggles** — one-click PATCH calls update the note in place
- **Tag display** — tags shown as styled chips on each note card
- **XSS protection** — user-supplied content is HTML-escaped before rendering

### Design spec

A full UX specification is available at `designs/frontend-ux.md`. It covers
layout wireframes, interaction patterns, colour palette, typography, and
accessibility requirements.

---

## Testing

The test suite uses **pytest** with a `TestClient` fixture that wraps the
FastAPI app (via Starlette's test client, powered by `httpx`). Each test class
or module gets a clean storage state via the `reset_storage()` fixture.

### Running the tests

```bash
# Run the full suite from the workspace root
cd /workspace
python -m pytest notes_app/tests/ -v

# Run a specific file
python -m pytest notes_app/tests/test_users_notes_tags.py -v

# Run with short summary only
python -m pytest notes_app/tests/ -q
```

### Test files

| File | Tests | Coverage area |
|------|-------|---------------|
| `test_users_notes_tags.py` | 30 | Users (5), Notes (15), Tags (8), search, toggles |
| `test_notebooks.py` | 14 | Notebook CRUD, cascade delete, list notes |
| `test_shares.py` | 16 | Share/unshare, idempotency, list shares |
| `test_notebooks_shares.py` | 32 | Full integration: notebooks + shares + cascade |
| **Total** | **92** | All 24 endpoints + edge cases |

### Key test patterns

- **Storage reset** — `conftest.py` calls `storage.reset_storage()` before each
  test to guarantee isolation between tests
- **201 / 204 status codes** — creation and deletion status codes verified
  explicitly, not just the response body
- **Toggle verification** — pin and archive tests call the toggle twice and
  assert the boolean returns to its original value
- **Idempotency checks** — sharing and tag-adding are tested with duplicate
  calls to assert no duplicates are created
- **Cascade assertions** — deleting a notebook verifies affected notes have
  `notebook_id: null`; deleting a note verifies its shares are removed

---

## Design Decisions

### In-memory storage (ADR-001)

All data is stored in module-level Python dicts and lists in `storage.py`.
There is no database dependency. This makes the project trivially installable
with `pip install -r requirements.txt` and immediately runnable.

**Trade-off:** data does not survive server restarts. For a production
deployment, replace `storage.py` with a database adapter (e.g. SQLAlchemy +
PostgreSQL) without touching any router code — the routers depend only on the
public API of `storage.py`.

### Route ordering: `/notes/search` before `/notes/{note_id}` (ADR-002)

FastAPI matches routes in the order they are registered. If
`GET /notes/{note_id}` were declared first, a request to
`GET /notes/search?q=foo` would be matched with `note_id = "search"` and
return a 404 instead of search results. The fix is structural: declare the
concrete literal path first, the parameterised path second.

### Tags embedded in notes

Tags are stored as a `list[str]` inside each note dict. There is no separate
tag table. This keeps the storage model simple and avoids joins. The trade-off
is that `GET /tags` requires a full scan of all notes; acceptable for an
in-memory store at this scale.

### Shares as a flat list

`storage.shares` is a Python `list[dict]` rather than a dict keyed on
`(note_id, user_id)`. Iteration is O(n) on the number of shares, which is
acceptable for in-memory storage. The idempotency check on share creation and
the cascade delete on note deletion both iterate this list.

### Cascading deletes

- **Notebook deleted** → all notes with `notebook_id == deleted_id` have their
  `notebook_id` set to `null`. Notes are **not** deleted.
- **Note deleted** → all share records for that note are removed from
  `storage.shares`.

### Case-insensitive username uniqueness

The duplicate-username check in `POST /users` compares both sides lowercased:
`u["username"].lower() == body.username.lower()`. This means `"Alice"`,
`"alice"`, and `"ALICE"` are treated as the same username, preventing
confusing duplicate accounts.

### Idempotent operations

Two operations are explicitly idempotent:

- **Share a note** — calling `POST /notes/{id}/share` with the same `user_id`
  twice returns the existing share record, not a new one.
- **Add a tag** — calling `POST /notes/{id}/tags` with a label that already
  exists on the note silently skips the append.

---

## License

MIT
