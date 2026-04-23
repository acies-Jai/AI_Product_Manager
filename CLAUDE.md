# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zepto PM Assistant — an agentic AI assistant for Product Managers at Zepto. It reads structured markdown knowledge files, answers PM questions via RAG with RBAC, generates six strategic artifacts (Roadmap, Key Focus Areas, Requirements, Success Metrics, Impact Quadrant, RICE Score), and facilitates cross-departmental communication via email.

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

Triggered by ⚡ Generate Artifacts button. Runs 8 hardcoded semantic queries against the vector store, deduplicates chunks, sends to Groq with a structured prompt, and parses 6 artifacts using delimiter tokens (`===ROADMAP===`, `===KEY_FOCUS_AREAS===`, `===RICE_SCORE===`, etc.). Saves to `outputs/` and sends notification emails. `load_saved_artifacts()` reloads them on app startup so tabs render without re-generating.

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

## System Documentation

See `SYSTEM_GUIDE.md` for a full end-to-end explanation of all system layers, data flow diagrams, RBAC details, hallucination guards, and a 10-question FAQ for demos and onboarding.
