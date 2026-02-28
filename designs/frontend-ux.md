# Note-Taking App Frontend — UX Design

> **Implementation status:** `templates/index.html` already exists and
> implements this spec. This document is the authoritative design reference for
> review, QA, and any future changes.

---

## User Story

As a user, I want a single-page frontend that lets me **create notes**,
**browse all my notes**, and **search** them by keyword — without leaving the
page or installing anything.

---

## User Flow

```
Page load
  │
  └─► loadNotes() fires automatically
        │
        ├─ success → note cards rendered in #notes-list
        └─ failure → inline error message in #notes-list

[Search bar]
  User types query → presses Enter or clicks "Search"
        │
        ├─ q non-empty → fetch GET /notes/search?q={q} → re-render #notes-list
        └─ q empty     → fetch GET /notes             → re-render #notes-list (show all)

  User clicks "Clear" → clears input + re-fetches all notes

[Create Note form]
  User fills User ID + Title + Content → clicks "Create Note"
        │
        ├─ any field empty       → inline validation message (no network call)
        ├─ user_id not found     → API returns 404 → error shown in #status-msg
        ├─ network/other error   → error shown in #status-msg
        └─ success (201)         → form fields cleared, #status-msg shows "✅ Note created!",
                                   auto-fades after 3 s, loadNotes() refreshes list
```

---

## Screen Layout

### Single-page, centred column

```
┌──────────────────────────────────────────────────┐
│ 📝  Note-Taking App                    [header]  │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 🔍 SEARCH NOTES                            │  │
│  │  [search input ──────────────] [Search][X] │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ ✏️ CREATE NOTE                              │  │
│  │  User ID  [_______________________]         │  │
│  │  Title    [_______________________]         │  │
│  │  Content  [                       ]         │  │
│  │           [        textarea       ]         │  │
│  │  [+ Create Note]                            │  │
│  │  {status message}                           │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 📋 ALL NOTES                               │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │◀ Note title              [📌][🗃️]   │  │  │
│  │  │  Note content preview…               │  │  │
│  │  │  #tag1  #tag2                        │  │  │
│  │  │  ID: 1 · User: 2 · Created: Jan 1   │  │  │
│  │  └──────────────────────────────────────┘  │  │
│  │  … more note cards …                       │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Section order (top → bottom):** Search → Create → List  
Rationale: users typically search before creating (to avoid duplicates), and
the list is the "result" of both actions so it sits at the bottom where eyes
naturally rest after interacting above.

**Column width:** `max-width: 860px`, centred with `margin: 0 auto`.  
Rationale: keeps content readable on desktop without line lengths becoming
uncomfortable; on mobile the column fills the viewport.

---

## Component Specs

### Header

| Property | Value |
|---|---|
| Element | `<header>` |
| Background | `#4a6fa5` (brand blue) |
| Text | `#ffffff`, 1.4 rem, weight 600 |
| Icon | 📝 emoji, 1.6 rem, left-aligned inline |
| Shadow | `0 2px 4px rgba(0,0,0,0.15)` — separates from page |
| No interactive elements | — |

---

### Card Wrapper (`.card`)

All three sections live inside a `.card`:

| Property | Value |
|---|---|
| Background | `#ffffff` |
| Border radius | `8px` |
| Padding | `1.5rem` |
| Shadow | `0 1px 3px rgba(0,0,0,0.1)` |
| Section heading | `.card h2` — `1rem`, uppercase, `0.05em` letter-spacing, `#4a6fa5` |

---

### Search Bar

| Component | CSS class | States & Behaviour |
|---|---|---|
| Text input | (inline in `.search-row`) | default, focus (blue border + ring), filled |
| Search button | `.btn .btn-search` | default `#667eea`, hover `#5a67d8`, active scale 0.97 |
| Clear button | `.btn .btn-clear` | default `#e2e8f0 / #4a5568`, hover `#cbd5e0` |

- **Enter key** on the search input triggers `doSearch()` — same as clicking Search
- **Empty query** → Clear button OR pressing Search with blank input both call `loadNotes()` (show all)
- No debounce — search fires on explicit user action only (button click / Enter)

---

### Create Note Form

| Field | ID | Type | Required | Placeholder |
|---|---|---|---|---|
| User ID | `#create-user-id` | `<input type="text">` | Yes | `e.g. 1` |
| Title | `#create-title` | `<input type="text">` | Yes | `Note title` |
| Content | `#create-content` | `<textarea>` | Yes | `Write your note here…` |

| Component | CSS class | States |
|---|---|---|
| All text inputs | — | default (border `#cbd5e0`), focus (border `#4a6fa5` + shadow ring) |
| Textarea | — | same as inputs; `resize: vertical`; `min-height: 90px` |
| Submit button | `.btn .btn-primary` | default `#4a6fa5`, hover `#3a5a8f`, active scale 0.97 |
| Status message | `#status-msg` | hidden (empty string) → success `.msg-ok` green → error `.msg-err` red |

**Validation rule:** all three fields must be non-empty before fetch fires.
Client-side check shows error in `#status-msg`; no red border on fields
(keep it simple).

**Post-success behaviour:**
1. Title and Content fields clear (User ID is kept — user may create multiple notes)
2. `#status-msg` shows "✅ Note created!" in green
3. After 3 seconds `#status-msg` clears silently
4. `loadNotes()` fires immediately (list updates without user action)

---

### Note Card (`.note-card`)

```
┌──────────────────────────────────────────────────┐
│◀ Note Title                    [📌 PINNED]       │  ← .note-header
│                                                  │
│  Content text, pre-wrapped, truncated only by    │  ← .note-content
│  natural line breaks                             │
│                                                  │
│  #tag-one  #tag-two                              │  ← .note-tags / .tag-pill
│                                                  │
│  ID: abc · User: 1 · Created: Jan 5, 2025, 3pm  │  ← .note-meta
└──────────────────────────────────────────────────┘
```

| CSS class | Meaning | Visual signal |
|---|---|---|
| `.note-card` | base card | `border-left: 4px solid #4a6fa5` (blue) |
| `.note-card.pinned` | note is pinned | left border changes to `#f6ad55` (amber) |
| `.note-card.archived` | note is archived | left border changes to `#a0aec0` (grey), `opacity: 0.75` |
| `.badge-pin` | "📌 Pinned" label | yellow pill |
| `.badge-archive` | "🗃 Archived" label | grey pill |
| `.tag-pill` | individual tag | blue-tinted pill `#ebf4ff / #2b6cb0` |
| `.note-meta` | timestamp/ID line | `0.75rem`, muted `#a0aec0` |

**Content rendering:** `white-space: pre-wrap; word-break: break-word` —
preserves user's line breaks, wraps long words, no truncation.

**XSS protection:** all user-supplied strings pass through `escHtml()` before
being inserted as innerHTML. Do not use `.innerHTML = rawUserContent` directly.

---

### Status / Feedback

| Class | Colour | When used |
|---|---|---|
| `.msg-ok` | `#276749` (green) | Successful create; auto-clears after 3 s |
| `.msg-err` | `#c53030` (red) | Validation failures, API errors, network errors; persists until next action |
| `.empty-state` | `#a0aec0` italic, centred | No notes returned (fresh app, filtered-to-zero, or search miss) |

---

## Interaction Notes

- **Loading state:** On page boot `#notes-list` displays `"Loading notes…"` in
  `.empty-state` style until `loadNotes()` resolves. No spinner — the load is
  fast for in-memory data.

- **Empty state (no notes):** Renders `<p class="empty-state">No notes found.</p>` —
  same element, different text from the loading state. Three distinct cases:
  1. App first run — no notes exist
  2. Search returned zero results
  3. All notes were deleted
  All three show the same message; differentiation is not required for this
  utility app.

- **Error state:** Inline only — errors appear in `#status-msg` (create form)
  or inside `#notes-list` as a `.empty-state.msg-err` paragraph (load/search).
  No modals, no toasts, no banners.

- **Success feedback:** In-place text in `#status-msg`. Auto-fades at 3 s to
  avoid stale confirmation remaining visible. No animation needed.

- **Hover/Focus:**
  - Inputs: focus ring `box-shadow: 0 0 0 3px rgba(74,111,165,0.15)`
  - Buttons: background darkens on `:hover`; scale(0.97) on `:active`
  - Note cards: no hover state (read-only display, no clickable actions)

- **Keyboard:** Enter in search input fires search. No other keyboard
  shortcuts.

- **No transitions/animations** beyond button scale — vanilla CSS only,
  no animation libraries.

---

## Color & Typography

| Token | Hex | Usage |
|---|---|---|
| Brand blue | `#4a6fa5` | Header bg, section headings, input focus border, primary button, note card left border (default) |
| Brand blue dark | `#3a5a8f` | Primary button hover |
| Accent purple | `#667eea` | Search button |
| Accent purple dark | `#5a67d8` | Search button hover |
| Pinned amber | `#f6ad55` | Pinned note left border |
| Archived grey | `#a0aec0` | Archived note left border, meta text, empty state text |
| Success green | `#276749` | `.msg-ok` status text |
| Error red | `#c53030` | `.msg-err` status text |
| Page background | `#f0f4f8` | `<body>` bg |
| Card background | `#ffffff` | `.card` bg |
| Note card bg | `#f7fafc` | `.note-card` bg (slightly off-white) |
| Border default | `#cbd5e0` | Input borders, note card border |
| Text body | `#2d3748` | `<body>` default text |
| Text muted | `#4a5568` | Labels, note content, meta |
| Tag pill bg | `#ebf4ff` | `.tag-pill` background |
| Tag pill text | `#2b6cb0` | `.tag-pill` text |

**Font stack:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`  
**Body size:** `0.95rem` inputs / `0.9rem` note content / `0.85rem` labels / `0.75rem` meta  
**Heading:** `1rem`, uppercase, `letter-spacing: 0.05em`  
**Spacing unit:** `8px` (0.5rem increments throughout)

---

## CSS Class Reference

> Quick lookup for developers implementing or modifying the template.

| Class | Element | Purpose |
|---|---|---|
| `.card` | `<div>` | White section panel with shadow |
| `.form-group` | `<div>` | Wraps label + input pair, flex column |
| `.btn` | `<button>` | Base button style |
| `.btn-primary` | `<button>` | Create Note (blue) |
| `.btn-search` | `<button>` | Search (purple) |
| `.btn-clear` | `<button>` | Clear search (grey) |
| `.search-row` | `<div>` | Flex row: input + 2 buttons |
| `#notes-list` | `<div>` | Grid container for note cards |
| `.note-card` | `<div>` | Individual note card |
| `.note-card.pinned` | — | Modifier: amber left border |
| `.note-card.archived` | — | Modifier: grey border, reduced opacity |
| `.note-header` | `<div>` | Flex row: title + badges |
| `.note-title` | `<span>` | Bold note title |
| `.note-badges` | `<span>` | Flex container for status badges |
| `.badge` | `<span>` | Base pill badge |
| `.badge-pin` | `<span>` | "📌 Pinned" badge |
| `.badge-archive` | `<span>` | "🗃 Archived" badge |
| `.note-content` | `<div>` | Note body text (pre-wrap) |
| `.note-tags` | `<div>` | Flex wrap row of tag pills |
| `.tag-pill` | `<span>` | Individual `#tag` pill |
| `.note-meta` | `<div>` | Muted ID / user / timestamp line |
| `#status-msg` | `<p>` | Create form feedback |
| `.msg-ok` | modifier | Green success text |
| `.msg-err` | modifier | Red error text |
| `.empty-state` | `<p>` | Centred italic placeholder text |

---

## Responsive Considerations

This is a utility/developer tool — full responsive design is out of scope.
Minimum viable mobile behaviour is handled by:

- `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- `max-width: 860px` column with `padding: 0 1rem` — narrows gracefully on
  small screens
- All inputs are `width: 100%` — no horizontal overflow
- `.search-row` is `display: flex` — wraps naturally if needed

No breakpoint media queries are required at this scope.

---

## Open Questions

- [ ] **User ID field in Create form** — the API requires a `user_id` but there
  is no auth layer. Should the frontend eventually auto-populate this from a
  "current user" session, or is a manual text field acceptable for the MVP?
  (Current implementation: manual text field. Acceptable for now.)
