# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zepto PM Assistant — an agentic AI assistant for Product Managers at Zepto. It reads structured markdown knowledge files, answers PM questions via RAG with RBAC, generates strategic artifacts (roadmaps, requirements, success metrics, impact quadrants), and facilitates cross-departmental communication via email.

**LLM Provider:** Groq (`llama-3.3-70b-versatile`)  
**Vector DB:** ChromaDB (persistent in `.chroma/`)  
**UI:** Streamlit

## Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment (required: GROQ_API_KEY)
cp .env.example .env

# Start the app
streamlit run app.py
# Available at http://localhost:8501
```

Optional env vars: `GMAIL_SENDER`, `GMAIL_APP_PASSWORD` — if absent, emails are logged to `outputs/email_log.txt` instead of sent.

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

### Agentic Loop: `core/agent.py`

`run_agent()` runs a for-loop calling Groq with 6 tool definitions. On each iteration:
- Structured `tool_calls` from the API response → dispatched via `run_tool()`
- Plain-text tool calls (fallback path) → parsed via regex (see known bug below)
- Content with no tools → final reply returned

**Known Bug (lines ~10–23):** The text-fallback regex only matches `=tool_name:` prefix (equals sign). The model sometimes outputs `-tool_name:` (dash prefix), causing the search to silently fail and returning a monologue. Fix: change the regex to `r'[-=](\w+):\s*["\']?(.+?)["\']?\s*$'`.

### Tool System: `core/tools.py`

6 tools dispatched by `run_tool()`:

| Tool | Purpose |
|------|---------|
| `search_context` | Semantic search across `inputs/` with RBAC filtering |
| `send_email` | Send or log email to list of addresses |
| `read_file` | Read full content of a single input doc |
| `propose_update_section` | Stage a `## Heading` section replacement (requires confirmation) |
| `propose_create_file` | Stage creating a new `.md` in `inputs/` (requires confirmation) |
| `propose_delete_file` | Stage file deletion (irreversible; requires confirmation) |

`propose_*` tools don't write immediately — they append to `pending_writes` and the user confirms via UI.

### RAG & RBAC: `rag.py`

`VectorStore` chunks input docs by `## ` markdown headers, tags each chunk with `{file, section, classification}` from `config/access_config.yaml`, and stores in ChromaDB. Searches are filtered via `where={"classification": {"$in": role_allowed_levels}}`.

Three classification levels: `open` → `internal` → `restricted`.  
Role permissions are defined in `config/access_config.yaml`. `finance.md` and `sales.md` are `restricted` (only PM, Finance, Leadership).

### Artifact Generation: `core/artifacts.py`

Triggered by ⚡ Generate Artifacts button. Runs 7 hardcoded semantic queries against the vector store, deduplicates chunks, sends to Groq with a structured prompt, and parses 5 artifacts using delimiter tokens (`===ROADMAP===`, `===KEY_FOCUS_AREAS===`, etc.). Saves to `outputs/` and sends notification emails.

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

1. **Text tool call regex bug** (`core/agent.py` lines ~10–23) — see above
2. **No test suite** — all testing is manual via UI
3. **Hardcoded artifact queries** — `_ARTIFACT_QUERIES` in `artifacts.py` are fixed; not configurable
4. **No web search** — agent can only search internal documents
5. **Session state fragility** — state lost on server restart; migration to LangGraph planned (see `HANDOFF.md`)

## Migration Target: LangGraph

`HANDOFF.md` documents a planned migration from the hand-rolled agentic loop to a LangGraph state machine with nodes: `classify_intent → retrieve_context → generate_response → stage_file_edit / send_notification / generate_artifacts → human_confirm`. The proposed `PMState` TypedDict and node decomposition are documented there.
