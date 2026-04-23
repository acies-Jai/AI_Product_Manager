# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zepto PM Assistant — an agentic AI assistant for Product Managers at Zepto. It reads structured markdown knowledge files, answers PM questions via RAG with RBAC, generates six strategic artifacts (Roadmap, Key Focus Areas, Requirements, Success Metrics, Impact Quadrant, RICE Score), and facilitates cross-departmental communication via email.

**LLM Provider:** Groq (`llama-3.3-70b-versatile`)  
**Vector DB:** ChromaDB (persistent in `.chroma/`)  
**Frontend:** React 18 + TypeScript + Vite + Tailwind CSS (in `frontend/`)  
**Backend API:** FastAPI (`server.py`) on port 8502

## Setup & Running

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment (required: GROQ_API_KEY)
cp .env.example .env

# 3. Start the FastAPI backend
python -m uvicorn server:app --port 8502

# 4. In a second terminal — install and start the React frontend
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

Optional env vars: `GMAIL_SENDER`, `GMAIL_APP_PASSWORD` — if absent, emails are logged to `outputs/email_log.txt` instead of sent.

> `app.py` (Streamlit) is retained as a fallback reference but is no longer the primary UI. `streamlit` and `plotly` are not in `requirements.txt`.

## Architecture

### Entry Point: `app.py`

The sole entry point. Manages Streamlit session state, renders the sidebar (reload files, index docs, generate artifacts), the main artifact display area, and the Live Communication Window (role-based chat).

Execution flow for a chat message:
```
User selects role → types prompt
→ run_agent(prompt, history, vs, role) [core/agent.py]
→ Agentic loop (max 8 iterations): Groq call → tool dispatch → tool result appended → repeat
→ Returns: reply + tool_events + pending_write
→ If pending_write: UI shows confirmation panel
→ User confirms → execute_write() → reload docs → reindex vector store
```

### Agentic Loop: `core/graph.py`

LangGraph `StateGraph` with four nodes: `classify_intent → retrieve_context → generate_response → human_confirm`. The `generate_response` node runs the Groq agentic loop (max 8 iterations) with 7 tools. Uses `MemorySaver` checkpointer keyed on `thread_id` (UUID per session).

- Structured `tool_calls` → dispatched via `run_tool()`
- Plain-text tool calls (fallback) → `_parse_text_tool_call()` regex (handles `[-=]?tool_name:` and bare `tool_name:`)
- Narration guard → detects model describing a search without calling the tool, injects a correction, retries
- Hallucination guard → `_should_deny_access()` intercepts replies with financial patterns when no valid search was made

`core/agent.py` is now only `log_message()` — the hand-rolled loop has been removed.

### Tool System: `core/tools.py`

7 tools dispatched by `run_tool()`:

| Tool | Purpose |
|------|---------|
| `search_context` | Semantic search across `inputs/` with RBAC filtering |
| `send_email` | Send or log email to list of addresses |
| `read_file` | Read full content of a single input doc |
| `propose_update_section` | Stage a `## Heading` section replacement (requires confirmation) |
| `propose_create_file` | Stage creating a new `.md` in `inputs/` (requires confirmation) |
| `read_inbox` | Read recent Gmail inbox messages via IMAP search string |
| `propose_update_section` | Stage a `## Heading` section replacement (requires confirmation) |
| `propose_create_file` | Stage creating a new `.md` in `inputs/` (requires confirmation) |
| `propose_delete_file` | Stage file deletion (irreversible; requires confirmation) |

`propose_*` tools don't write immediately — they append to `pending_writes` and the user confirms via UI. `send_email` rejects addresses not in `employees.md`.

### RAG & RBAC: `rag.py`

`VectorStore` chunks input docs by `## ` markdown headers, tags each chunk with `{file, section, classification}` from `config/access_config.yaml`, and stores in ChromaDB. Searches are filtered via `where={"classification": {"$in": role_allowed_levels}}`.

Three classification levels: `open` → `internal` → `restricted`.  
Role permissions are defined in `config/access_config.yaml`. `finance.md` and `sales.md` are `restricted` (only PM, Finance, Leadership).

### Artifact Generation: `core/artifacts.py`

Triggered by ⚡ Generate Artifacts button. Runs 8 hardcoded semantic queries against the vector store, deduplicates chunks, sends to Groq with a structured prompt, and parses 7 artifacts using delimiter tokens (`===ROADMAP===`, `===KEY_FOCUS_AREAS===`, `===RICE_SCORE===`, `===ROADMAP_TIMELINE===`, etc.). Saves to `outputs/`. `load_saved_artifacts()` reloads them on app startup.

Email notification is **decoupled** — a separate 📧 Notify Team button in the sidebar (and `POST /notify-team` API) sends the email when the PM chooses, not automatically on generation.

### File Operations: `core/files.py`

- `load_inputs()` — reads all `.md` from `inputs/`
- `execute_write(operation)` — applies staged writes (regex section replace, create, delete)
- `preview_write(operation)` — returns human-readable diff for the confirmation UI

### Configuration

- `config/access_config.yaml` — document classifications + role → allowed classification levels
- `config/email_config.yaml` — email triggers, department lead mappings, subject/body templates
- `core/client.py` — `MODEL` constant, `INPUTS_DIR`, `OUTPUTS_DIR`, Groq client init
- `.streamlit/config.toml` — UI theme (Zepto purple brand colors)

## Extending the System

- **New input documents:** Drop `.md` into `inputs/`, update `config/access_config.yaml`, re-index
- **New roles:** Add to `config/access_config.yaml` with allowed classification levels
- **New tools:** Add definition to `TOOLS` list in `core/tools.py`, add handler in `run_tool()`
- **New artifact types:** Add query to `_ARTIFACT_QUERIES` and add delimiter parsing in `artifacts.py`
- **Change LLM model:** Update `MODEL` in `core/client.py`

## Known Issues & Technical Debt

1. **No test suite** — all testing is manual via UI
2. **Hardcoded artifact queries** — `_ARTIFACT_QUERIES` in `artifacts.py` are fixed; not configurable
3. **No web search** — agent can only search internal documents
4. **MemorySaver is in-memory** — history lost on server restart; migrate to `SqliteSaver` for persistence
5. **Single pending_write at a time** — only one file change can be staged per turn

### API Server: `server.py`

FastAPI server for programmatic access and custom frontend integration.

```bash
python -m uvicorn server:app --port 8502
```

| Method | Path | Notes |
|--------|------|-------|
| `GET`  | `/health` | Status + chunk count |
| `GET`  | `/files` | File list + indexed flag |
| `POST` | `/index` | Re-index all inputs |
| `POST` | `/chat` | Synchronous chat; returns full reply |
| `POST` | `/chat/stream` | SSE streaming — yields one JSON event per graph node as it completes |
| `POST` | `/confirm` | Confirm/cancel a pending file write |
| `POST` | `/generate-artifacts` | Generate artifacts; pass `?notify=true` to also email |
| `POST` | `/notify-team` | Email the saved artifacts without regenerating |
| `GET`  | `/artifacts` | Retrieve saved artifact content |

CORS is enabled for `localhost:5173` (Vite) and `localhost:3000` (React/Next.js) to support a custom frontend.

**SSE stream format** (`/chat/stream`): each event is `data: {"node": "<name>", "updates": {...}, "thread_id": "..."}`. Final event has `"node": "__done__"`.

### Frontend: `frontend/`

React 18 + TypeScript + Vite app. Run with `npm run dev` from the `frontend/` directory.

**Stack:** React 18, TypeScript, Tailwind CSS (Zepto colour tokens in `tailwind.config.js`), Zustand for state, Recharts for charts, Lucide React for icons.

**Dev proxy:** Vite proxies `/api/*` → `http://localhost:8502` so all API calls use the relative `/api` base without CORS issues.

**Key files:**
- `src/types.ts` — all shared types (`Message`, `TaoStep`, `PendingWrite`, `Artifacts`) + `ROLE_CONFIG`, `ARTIFACT_KEYS`, `ARTIFACT_LABELS` constants
- `src/api.ts` — typed wrappers for every backend endpoint; `streamChat()` is an async generator over the SSE stream
- `src/store.ts` — Zustand store; single source of truth for `artifacts`, `messages`, `taoSteps`, `pendingWrite`, `role`, loading flags
- `src/App.tsx` — root layout: Sidebar (left) + TopBar/ArtifactPanel (centre) + ChatPanel (right)

**Component structure:**
```
components/
  Sidebar.tsx          — index/generate controls, file list, notify button
  TopBar.tsx           — hero header + status bar
  RoleSelector.tsx     — role dropdown with coloured badge
  ArtifactPanel.tsx    — tab switcher, delegates to artifact components
  ChatPanel.tsx        — message list, chat input, TaoStepper while streaming
  TaoStepper.tsx       — vertical timeline of graph node steps during a response
  PendingWriteCard.tsx — confirm/cancel panel for staged file writes
  StatusBar.tsx        — chunks / files / artifacts count strip
  Hero.tsx             — gradient banner
  artifacts/
    RoadmapTab.tsx     — Now/Next/Later Kanban + Recharts Gantt timeline
    RiceTab.tsx        — horizontal Recharts bar chart + raw table toggle
    MetricsTab.tsx     — styled table with owner pill badges
    QuadrantTab.tsx    — 2×2 impact/effort grid
    KeyFocusTab.tsx    — numbered focus areas
    RequirementsTab.tsx — requirements / scope / spec sections
    StyledTable.tsx    — reusable markdown table → HTML table renderer
```

## System Documentation

See `system_guide/` for topic-by-topic documentation. `system_guide/12_api_testing_guide.md` has complete curl commands for every endpoint.
