## ADR-001: In-Memory Storage with Module-Level Dicts

**Status:** Accepted

**Context:**
The note-taking API needs a storage layer. Acceptance criteria explicitly
forbid a database (AC44) and require that the app start with a single
`uvicorn` command without any infrastructure setup.

**Decision:**
Use module-level Python dicts and a list in `storage.py`:
- `users`, `notes`, `notebooks` — `dict[str, dict]` keyed by string ID
- `shares` — `list[dict]` (no natural unique key; list with index scan)
- Auto-increment integer counters wrapped in `next_*_id()` helpers
- `reset_storage()` exported for use in pytest fixtures

Tags are embedded directly inside each note dict as `list[str]` rather than
a separate data structure, because all tag operations resolve from the note
and a separate index would add complexity with no throughput benefit.

**Consequences:**
- ✅ Zero infrastructure — works out of the box
- ✅ Tests are fully isolated via `reset_storage()`
- ✅ Storage layer is a single, easy-to-read file
- ⚠️ All data is lost on server restart (by design for this API)
- ⚠️ O(n) scans on shares list — acceptable at in-memory scale
- ⚠️ Replacing with a DB requires router changes only at the storage call-sites
