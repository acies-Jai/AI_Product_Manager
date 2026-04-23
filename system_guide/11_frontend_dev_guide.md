# 11 — React Frontend Developer Guide
### Everything you need to work on `frontend/`

This guide is for someone who knows React but is new to this project. It covers
the full stack, the data flow, the state model, and how to extend each part.

---

## Stack at a glance

| Layer | Technology | Why |
|-------|-----------|-----|
| Framework | React 18 + TypeScript | Component model, strict typing |
| Build tool | Vite 5 | Fast HMR, first-class TypeScript |
| Styling | Tailwind CSS 3 | Utility-first, Zepto tokens in `tailwind.config.js` |
| State | Zustand | Single store, no context boilerplate |
| Charts | Recharts | React-native chart library |
| Icons | Lucide React | Consistent SVG icon set |
| API | Fetch + SSE | Native browser APIs, no extra dependency |

The previous UI was Streamlit (Python). The React app calls the same FastAPI
backend (`server.py`) via a Vite dev proxy — no CORS config needed in dev.

---

## Running locally

```bash
# Terminal 1 — backend (must be running first)
python -m uvicorn server:app --port 8502

# Terminal 2 — frontend
cd frontend
npm install        # first time only
npm run dev        # http://localhost:5173
```

The Vite config (`vite.config.ts`) proxies every `/api/*` request to
`http://localhost:8502`, stripping the `/api` prefix:

```ts
proxy: {
  '/api': {
    target: 'http://localhost:8502',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
},
```

So `fetch('/api/artifacts')` hits `http://localhost:8502/artifacts` transparently.

---

## App layout

```
┌─────────────┬────────────────────────────┬──────────────────┐
│  Sidebar    │  TopBar (Hero + StatusBar) │                  │
│  (240px)    ├────────────────────────────┤   ChatPanel      │
│             │  ArtifactPanel             │   (380px)        │
│             │  (scrollable)              │                  │
└─────────────┴────────────────────────────┴──────────────────┘
```

`App.tsx` sets up this layout with Tailwind flex:
```tsx
<div className="flex h-screen overflow-hidden bg-zepto-bg">
  <Sidebar />
  <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
    <TopBar />
    <div className="flex-1 min-h-0 overflow-y-auto p-5">
      <ArtifactPanel />
    </div>
  </div>
  <ChatPanel />
</div>
```

On mount, `loadInitial()` fires once to fetch `/api/files` and `/api/artifacts`
in parallel, populating the store.

---

## Colour tokens

Defined in `tailwind.config.js` under `theme.extend.colors.zepto`:

| Token | Hex | Used for |
|-------|-----|---------|
| `zepto-purple` | `#5E17EB` | Primary actions, headings, badges |
| `zepto-light` | `#7C3AED` | Gradient end, hover |
| `zepto-pale` | `#9F67FA` | Gradient tail |
| `zepto-dark` | `#1A0533` | Sidebar background, headings |
| `zepto-bg` | `#F4F0FC` | App background |
| `zepto-tint` | `#F0EAFF` | Tab bar, chip backgrounds |
| `zepto-muted` | `#EDE9FF` | Borders, dividers |

Use `bg-zepto-purple`, `text-zepto-dark`, `border-zepto-muted`, etc. in Tailwind classes.

---

## Custom CSS classes (`src/index.css`)

Four reusable classes defined in the `@layer components` block:

| Class | What it renders |
|-------|----------------|
| `.card` | White card with `zepto-muted` border, subtle shadow, `rounded-2xl` |
| `.btn-primary` | Purple gradient button with hover lift and shadow |
| `.btn-ghost` | Transparent button with border, `zepto-purple` text |
| `.role-badge` | Coloured pill (inline-flex, rounded-full) — pass `style` for dynamic colour |

Markdown content rendered inside artifact tabs uses the `.prose` block for
typography. The `pre` and `code` elements inside it are overridden to use the
Zepto tint background.

---

## Types (`src/types.ts`)

All shared interfaces live here. Key ones:

```ts
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  roleLabel?: string        // set on user messages
  toolEvents?: ToolEvent[]  // set on assistant messages
}

interface TaoStep {
  id: string
  node: string    // 'classify_intent' | 'retrieve_context' | 'tool' | 'direct'
  label: string   // human-readable step name
  detail: string  // short description
  color: string   // hex, used for the timeline accent
  icon: string    // emoji
}

interface PendingWrite {
  tool: 'propose_update_section' | 'propose_create_file' | 'propose_delete_file'
  args: Record<string, string>
}
```

Constants also exported from here — use them instead of hardcoding strings:

```ts
ROLES              // string[] — all role names in display order
ROLE_CONFIG        // Record<string, { color, icon, access }>
ARTIFACT_KEYS      // readonly tuple — 6 artifact keys
ARTIFACT_LABELS    // Record<ArtifactKey, string> — display names
```

---

## API layer (`src/api.ts`)

All functions call `/api/*` (proxied to the backend). Each throws on non-2xx.

| Function | Endpoint | Returns |
|----------|---------|---------|
| `fetchFiles()` | `GET /files` | `{ files, indexed, chunks }` |
| `fetchArtifacts()` | `GET /artifacts` | `Record<string, string>` |
| `indexDocuments()` | `POST /index` | `{ chunks, files }` |
| `generateArtifacts()` | `POST /generate-artifacts?notify=false` | full artifacts response |
| `notifyTeam()` | `POST /notify-team` | `{ email_status }` |
| `confirmWrite(threadId, confirmed)` | `POST /confirm` | `{ reply }` |
| `streamChat(message, role, threadId)` | `POST /chat/stream` | async generator |

### The SSE streaming function

`streamChat` is an **async generator** — `yield`s one parsed event object per
SSE line as it arrives from the backend:

```ts
export async function* streamChat(message: string, role: string, threadId: string) {
  const res = await fetch('/api/chat/stream', { method: 'POST', ... })
  const reader = res.body.getReader()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''          // keep partial last line
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6))
      }
    }
  }
}
```

The buffer/split pattern handles chunked delivery — a single `read()` may
contain multiple SSE lines or a partial line. The incomplete last line is held
in `buffer` and prepended on the next read.

Consume it with `for await`:
```ts
for await (const event of streamChat(message, role, threadId)) {
  if (event.node === '__done__') break
  // event.node is one of: 'classify_intent', 'retrieve_context', 'generate_response'
  // event.updates contains the node's state updates
  // event.thread_id is the session ID
}
```

---

## State management (`src/store.ts`)

One Zustand store. Access it anywhere with `useStore(selector)`:

```ts
const artifacts = useStore(s => s.artifacts)
const sendMessage = useStore(s => s.sendMessage)
```

### Full state shape

```ts
chunksIndexed: number       // from /files
files: string[]             // from /files
artifacts: Artifacts        // from /artifacts
staleArtifacts: boolean     // set true when a doc is confirmed-written
role: string                // currently selected role
activeTab: string           // which artifact tab is showing
isIndexing: boolean         // loading flag for Index button
isGenerating: boolean       // loading flag for Generate button
messages: Message[]         // full chat history
isThinking: boolean         // true while SSE stream is in progress
taoSteps: TaoStep[]         // steps accumulating during stream; cleared after
pendingWrite: PendingWrite | null
threadId: string            // UUID, generated once on store init (not reset)
```

### Actions

| Action | What it does |
|--------|-------------|
| `loadInitial()` | Parallel fetch of `/files` + `/artifacts`; populates store on mount |
| `indexDocuments()` | Sets `isIndexing`, calls `/index`, updates `chunksIndexed` + `files` |
| `generateArtifacts()` | Sets `isGenerating`, calls `/generate-artifacts`, re-fetches artifacts, resets `staleArtifacts` |
| `sendMessage(text)` | Appends user message, opens SSE stream, accumulates `taoSteps`, appends assistant message, sets `pendingWrite` |
| `confirmWrite(confirmed)` | Calls `/confirm`, appends reply message, clears `pendingWrite`, sets `staleArtifacts: confirmed` |
| `setRole(role)` | Updates `role` |
| `setActiveTab(tab)` | Updates `activeTab` |

### How `sendMessage` builds the TAO steps

```ts
for await (const event of api.streamChat(message, role, threadId)) {
  if (event.node === 'classify_intent')   → push { label: 'Order received', ... }
  if (event.node === 'retrieve_context')  → push { label: 'Packing context', ... }
  if (event.node === 'generate_response') → push one step per tool_event
                                            or one 'Express delivery' step if none
}
```

Steps accumulate into `taoSteps` as they arrive so the UI can render them
progressively. After the stream ends and the assistant message is appended,
`taoSteps` is reset to `[]`.

---

## Component responsibilities

### Layout components

**`Sidebar.tsx`**
- Branded header ("⚡ Zepto")
- File list with indexed indicator per file
- Three action buttons: Index Documents, ⚡ Generate Artifacts, 📧 Notify Team
- Artifact progress bar (n/6 complete)
- Reads: `files`, `chunksIndexed`, `isIndexing`, `isGenerating`, `artifacts`
- Calls: `indexDocuments()`, `generateArtifacts()`, `notifyTeam()` (direct API call)

**`TopBar.tsx`**
- Renders `<Hero />` + `<StatusBar />`
- Also contains `<RoleSelector />` inline

**`Hero.tsx`**
- Purple gradient banner, tagline, chunk count badge

**`StatusBar.tsx`**
- `{chunks} sources indexed · {n} knowledge files · {n}/6 artefacts ready`
- Shows stale-artifacts warning + Regenerate button when `staleArtifacts` is true

**`RoleSelector.tsx`**
- `<select>` over `ROLES`; calls `setRole()` on change
- Coloured badge showing current role's icon, name, and access level

### Chat components

**`ChatPanel.tsx`**
- Fixed right column, 380px wide
- Renders `messages` as `<MessageBubble>` components
- Shows `<TaoStepper>` when `isThinking` is true
- Shows `<PendingWriteCard>` when `pendingWrite` is set
- Text area input — submits on Enter (Shift+Enter for newline)
- Suggested prompt chips shown when `messages` is empty

**`TaoStepper.tsx`**
- Renders `taoSteps` as a vertical timeline
- Each step: left-side coloured bar + dot, label (bold, coloured), detail (grey)
- Animated "typing" indicator at the bottom while `isThinking`

**`PendingWriteCard.tsx`**
- Amber card for update/create; red card for delete
- Shows operation type, filename, heading or content preview
- Confirm and Cancel buttons → call `confirmWrite(true/false)`

### Artifact panel

**`ArtifactPanel.tsx`**
- Tab bar using `ARTIFACT_KEYS` + `ARTIFACT_LABELS`
- Active tab tracked in store (`activeTab`)
- Shows loading skeleton when `isGenerating`
- Shows onboarding card when no artifacts
- Delegates to the correct `*Tab` component based on `activeTab`

**Tab components** (all in `components/artifacts/`):

| Component | Input | Renders |
|-----------|-------|---------|
| `RoadmapTab` | `roadmap` + `roadmap_timeline` (optional) | Kanban columns + Recharts Gantt |
| `RiceTab` | `rice_score` | Recharts horizontal bar chart + collapsible table |
| `MetricsTab` | `success_metrics` | Styled table with owner colour badges |
| `QuadrantTab` | `impact_quadrant` | 2×2 grid of coloured cards |
| `KeyFocusTab` | `key_focus_areas` | Numbered cards with title + bullets |
| `RequirementsTab` | `requirements` | Sectioned cards (Requirements / Scope / Spec) |

**`StyledTable.tsx`** — shared utility component that takes a markdown table
string and renders it as a styled HTML table with configurable column templates
and cell renderers. Used by MetricsTab and anywhere else a table is needed.

---

## Parsing patterns

Every tab receives the raw LLM output string and must parse it defensively.
The standard pattern used across tabs:

```ts
function parseMarkdownTable(content: string): string[][] {
  const lines = content.split('\n').filter(l => l.trim().startsWith('|'))
  return lines
    .filter(l => !l.replace(/\|/g, '').trim().match(/^[-: ]+$/))  // skip separator
    .map(l => l.split('|').slice(1, -1).map(c => c.trim()))
}
```

- Row 0 is always the header
- Rows 1+ are data rows
- Handle empty strings and missing cells with `.at(i) ?? ''`

For the roadmap timeline dates, `RoadmapTab` parses `"Mon YYYY"` strings:
```ts
new Date(`1 ${cell}`)  // e.g. new Date("1 Apr 2026")
```

For the impact quadrant, `QuadrantTab` parses the `--SECTION--` delimiter
format (same logic as the Python `parse_quadrant_sections()` in `core/artifacts.py`).

---

## Adding a new artifact tab

1. **Backend** — add the delimiter and key to `core/artifacts.py` (see `09_artifacts_and_rice.md`)
2. **`types.ts`** — add the key to `ARTIFACT_KEYS` and a label to `ARTIFACT_LABELS`
3. **Create** `src/components/artifacts/NewTab.tsx` — accept `content: string`, parse and render
4. **`ArtifactPanel.tsx`** — import the new component and add a `case` in the tab switcher

That's the full change surface. The store, API, and backend all pick up new artifact keys automatically because they use `Record<string, string>`.

---

## Adding a new API call

1. Add a typed function to `src/api.ts` using the same `fetch` + `throw on !res.ok` pattern
2. Add the action to the store interface in `src/store.ts` and implement it
3. Wire the action to whatever UI element triggers it

Do not call `api.*` functions directly from components — put all API calls through the store so loading flags and state updates stay consistent.

---

## What NOT to change

- Do not rename `ARTIFACT_KEYS` values — they must match the keys returned by `GET /api/artifacts` and the filenames in `outputs/`
- Do not change the `threadId` generation in the store — it is set once at store init; resetting it starts a new conversation session and loses multi-turn memory
- Do not remove the `buffer` logic in `streamChat()` — it is required to handle chunked SSE delivery correctly
- Do not bypass the store for API calls — always go through store actions so `isThinking`, `isIndexing`, etc. stay in sync with the UI
- Do not add `streamlit` or `plotly` back to `requirements.txt` — the backend no longer needs them

---

## Testing the frontend

```bash
# 1. Confirm backend is running
curl http://localhost:8502/health

# 2. Start frontend
cd frontend && npm run dev

# 3. Verify three states:
#    a. No artifacts yet: should show the onboarding card
#    b. After clicking Index: chunk count badge updates
#    c. After Generate Artifacts: all 6 tabs populate

# 4. Chat test (use the /api testing guide for curl equivalents):
#    - Select "Product Manager", ask about budget → real data
#    - Select "Design", ask about budget → access denied message
#    - Ask anything → TAO stepper shows steps during stream
#    - Ask to update a doc → PendingWriteCard appears, Confirm writes file
```
