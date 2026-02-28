# Note-Taking REST API — Architecture

## Overview

A full-featured note-taking REST API built with FastAPI and fully in-memory
storage. Five domain routers expose 22+ endpoints covering users, notes, tags,
notebooks, and sharing. A Jinja2-served single-page frontend at `GET /`
provides list, create, and search functionality without a build step.

## Components

| Component | File | Role |
|---|---|---|
| App entry | `main.py` | Creates FastAPI app, mounts routers, serves frontend |
| Storage | `storage.py` | Module-level dicts; `reset_storage()` for tests |
| Models | `models.py` | Pydantic request/response models |
| Users router | `routers/users.py` | User CRUD (AC6-AC8) |
| Notes router | `routers/notes.py` | Note CRUD + search + pin/archive + notebook assign |
| Tags router | `routers/tags.py` | Tag add/remove + global tag listing (AC15-AC18) |
| Notebooks router | `routers/notebooks.py` | Notebook CRUD + note listing (AC25-AC30) |
| Shares router | `routers/shares.py` | Share/unshare + visibility listing (AC31-AC34) |
| Frontend | `templates/index.html` | Vanilla HTML/CSS/JS; calls REST API (AC35-AC38) |

## Data Flow

```
Browser
  │
  ├─ GET /             → main.py → Jinja2 → index.html
  │                       (frontend JS then calls REST endpoints below)
  │
  ├─ POST /users        → users.py  → storage.users
  ├─ POST /notes        → notes.py  → storage.notes  (validates user_id)
  ├─ GET  /notes/search → notes.py  → storage.notes  (case-insensitive scan)
  ├─ GET  /notes/{id}   → notes.py  → storage.notes
  ├─ PATCH /notes/{id}/pin|archive → notes.py → storage.notes
  │
  ├─ POST /notes/{id}/tags   → tags.py  → storage.notes[id]["tags"]
  ├─ GET  /tags              → tags.py  → scan all storage.notes
  │
  ├─ POST /notebooks         → notebooks.py → storage.notebooks
  ├─ PUT  /notes/{id}/notebook→ notes.py   → storage.notes[id]["notebook_id"]
  ├─ DELETE /notebooks/{id}  → notebooks.py → storage.notebooks
  │                               + nullify storage.notes[*]["notebook_id"]
  │
  ├─ POST /notes/{id}/share  → shares.py → storage.shares (append)
  ├─ DELETE /notes/{id}/share/{uid} → shares.py → storage.shares (remove)
  └─ GET  /users/{id}/shared → shares.py → join storage.shares + storage.notes
```

## API Contracts

### Users
| Method | Path | Body | Status | Response |
|---|---|---|---|---|
| POST | `/users` | `{username, email}` | 201 / 409 | UserOut |
| GET | `/users/{user_id}` | — | 200 / 404 | UserOut |

### Notes
| Method | Path | Body / Query | Status | Response |
|---|---|---|---|---|
| POST | `/notes` | `{title, content, user_id}` | 201 / 404 | NoteOut |
| GET | `/notes/search` | `?q=<str>` | 200 | List[NoteOut] |
| GET | `/notes/{note_id}` | — | 200 / 404 | NoteOut |
| GET | `/notes` | `?user_id, ?pinned, ?archived` | 200 | List[NoteOut] |
| PUT | `/notes/{note_id}` | `{title?, content?}` | 200 / 404 | NoteOut |
| DELETE | `/notes/{note_id}` | — | 204 / 404 | — |
| PATCH | `/notes/{note_id}/pin` | — | 200 / 404 | NoteOut |
| PATCH | `/notes/{note_id}/archive` | — | 200 / 404 | NoteOut |
| PUT | `/notes/{note_id}/notebook` | `{notebook_id}` | 200 / 404 | NoteOut |

### Tags
| Method | Path | Body | Status | Response |
|---|---|---|---|---|
| POST | `/notes/{note_id}/tags` | `{label}` | 200 / 404 | NoteOut |
| DELETE | `/notes/{note_id}/tags/{tag}` | — | 200 / 404 | NoteOut |
| GET | `/tags` | — | 200 | List[str] |
| GET | `/tags/{tag}/notes` | — | 200 | List[NoteOut] |

### Notebooks
| Method | Path | Body / Query | Status | Response |
|---|---|---|---|---|
| POST | `/notebooks` | `{name, user_id}` | 201 / 404 | NotebookOut |
| GET | `/notebooks` | `?user_id` | 200 | List[NotebookOut] |
| GET | `/notebooks/{notebook_id}` | — | 200 / 404 | NotebookOut |
| DELETE | `/notebooks/{notebook_id}` | — | 204 / 404 | — |
| GET | `/notebooks/{notebook_id}/notes` | — | 200 / 404 | List[NoteOut] |

### Shares
| Method | Path | Body | Status | Response |
|---|---|---|---|---|
| POST | `/notes/{note_id}/share` | `{user_id}` | 200 / 404 | ShareOut |
| GET | `/notes/{note_id}/shares` | — | 200 / 404 | List[ShareOut] |
| DELETE | `/notes/{note_id}/share/{user_id}` | — | 200 / 404 | dict |
| GET | `/users/{user_id}/shared` | — | 200 / 404 | List[NoteOut] |

## Data Model

```python
# storage.py — module-level globals

users: dict[str, dict] = {}
# user = {id, username, email, created_at}

notes: dict[str, dict] = {}
# note = {id, title, content, user_id, created_at, updated_at,
#         is_pinned, is_archived, tags: list[str], notebook_id}

notebooks: dict[str, dict] = {}
# notebook = {id, name, user_id, created_at}

shares: list[dict] = []
# share = {note_id, user_id, shared_at}
```

### Key design choices
- **Tags are embedded** in the note dict as a `list[str]` — no separate tag
  table needed for the in-memory scale of this API.
- **Shares use a flat list** rather than a dict; iteration is O(n) on shares
  which is acceptable for in-memory storage.
- **Notebook deletion cascades** by iterating notes and nullifying
  `notebook_id` — a cheap operation for in-memory data.
- **`/notes/search` declared before `/{note_id}`** — critical FastAPI route
  ordering to prevent "search" being matched as a path parameter.

## Non-Functional Considerations

- **Security:** No auth layer in this version. Input is validated by Pydantic.
  `escHtml()` in the frontend prevents XSS when rendering user-supplied note
  content.
- **Performance:** All lookups are O(n) dict scans; acceptable for in-memory
  storage. A production version would add indexes (e.g. inverted index for
  tags, user→notes index).
- **Scalability:** In-memory storage is deliberately ephemeral. Replace
  `storage.py` with a database adapter (SQLAlchemy/Motor) for persistence
  without touching the router layer.
- **Testability:** `reset_storage()` in `storage.py` enables clean-slate unit
  tests via a pytest fixture.
