## ADR-002: GET /notes/search Declared Before GET /notes/{note_id}

**Status:** Accepted

**Context:**
FastAPI resolves routes in declaration order. If `GET /notes/{note_id}` is
declared before `GET /notes/search`, a request to `/notes/search` is matched
by the `{note_id}` path parameter handler with `note_id="search"`, causing a
misleading 404 instead of returning search results.

**Decision:**
In `routers/notes.py`, the search route is unconditionally placed before the
`/{note_id}` route in source code order. A prominent comment is added to
document this constraint so future developers do not accidentally reorder the
routes.

**Consequences:**
- ✅ Search works correctly as a keyword route, not as a note ID lookup
- ✅ Follows FastAPI's documented recommendation for static vs. dynamic segments
- ⚠️ Requires discipline: any future static sub-path of `/notes/*` must also
  be declared before `/{note_id}`
