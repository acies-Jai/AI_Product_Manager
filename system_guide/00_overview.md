# 00 — Project Overview & Architecture

## What this system does

The Zepto PM Assistant is an agentic AI tool that acts as an always-on second brain for a Product
Manager. It reads structured markdown files placed in `inputs/` by each department, answers
questions grounded in that data, generates six PM artefacts (Roadmap, Key Focus Areas,
Requirements, Success Metrics, Impact Quadrant, RICE Score), sends notification emails with the
artefact content, and lets any team member propose updates to the knowledge base through a chat
interface — all with role-based access control so restricted financial data stays protected.

---

## The five layers

```
┌─────────────────────────────────────────────────────────────┐
│  1. INPUT FILES   inputs/*.md                               │
│     One markdown file per department.                       │
│     PM drops files here; no manual prompting required.      │
└────────────────────────┬────────────────────────────────────┘
                         │ chunked by ## heading, tagged with
                         │ classification level
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. RAG + RBAC   rag.py  +  ChromaDB (.chroma/)             │
│     Each chunk stored with metadata:                        │
│       {file, section, classification}                       │
│     Searches filtered by caller's role.                     │
└────────────────────────┬────────────────────────────────────┘
                         │ role-filtered chunks
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. LANGGRAPH AGENT   core/graph.py                         │
│     classify_intent → retrieve_context →                    │
│     generate_response → [human_confirm]                     │
│     Groq llama-3.3-70b-versatile, up to 8 tool calls/turn  │
│     MemorySaver checkpointer preserves conversation history │
└────────────────────────┬────────────────────────────────────┘
                         │ reply + tool_events + pending_write
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ARTIFACTS   core/artifacts.py                           │
│     6 artefact types generated on-demand.                   │
│     Saved to outputs/*.md, loaded back on startup.          │
└────────────────────────┬────────────────────────────────────┘
                         │ notify on generation
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. EMAIL   core/email_service.py                           │
│     SMTP send (Gmail) + IMAP read.                          │
│     Falls back to email_log.txt if not configured.          │
└─────────────────────────────────────────────────────────────┘
```

---

## Data flow — one chat message, end-to-end

```
User selects role + types message
  │
  ▼  app.py — graph.stream(input_state, config, stream_mode="updates")
  │
  ├─► NODE: classify_intent
  │     One Groq call → intent label
  │     Labels: search_query | file_edit | email_request |
  │             artifact_request | general_chat
  │
  ├─► NODE: retrieve_context
  │     Skipped for artifact_request or general_chat.
  │     Otherwise: VectorStore.search(message, role=role, n=3)
  │     Returns role-filtered chunks injected as system context.
  │
  ├─► NODE: generate_response  [agentic loop, max 8 iterations]
  │     Build messages list:
  │       system prompt
  │       + pre-retrieved context (if any)
  │       + history (from checkpointer)
  │       + current user message
  │     │
  │     ├─ tool_calls present  → run_tool() → result appended → loop
  │     ├─ plain-text tool call → _parse_text_tool_call() → run_tool()
  │     │                         → final Groq call with results
  │     ├─ narration without    → inject correction message → continue
  │     │   tool call
  │     └─ no tool call         → reply ready → _make_return()
  │                               → _should_deny_access() guard fires
  │                                 if reply has financial patterns and
  │                                 no valid search was made
  │
  └─► NODE: human_confirm  [only if pending_write in state]
        interrupt() — graph execution pauses
        app.py renders confirm/cancel panel with diff preview
        │
        ├─ Confirm: Command(resume=True)
        │    execute_write() → regex section replace / create / delete
        │    reload inputs → reindex VectorStore → stale_artifacts=True
        │
        └─ Cancel: Command(resume=False)
             no file changes
  │
  ▼  app.py
  Render reply in st.chat_message("assistant")
  Show TAO trace inside st.status() expander
  Log to outputs/chat_log.txt
```

---

## File map — what lives where

| Concern | File |
|---------|------|
| Entry point, UI, session state | `app.py` |
| LangGraph graph, nodes, state | `core/graph.py` |
| Tool definitions + dispatch | `core/tools.py` |
| RAG, embeddings, RBAC filtering | `rag.py` |
| Artifact generation + parsing | `core/artifacts.py` |
| File read / write / preview | `core/files.py` |
| Email send + inbox read | `core/email_service.py` |
| Chat history logging | `core/agent.py` |
| Access config (roles, levels) | `config/access_config.yaml` |
| Email config (recipients, templates) | `config/email_config.yaml` |
| LLM client, paths, constants | `core/client.py` |
| UI theme | `.streamlit/config.toml` |

---

## Glossary of terms used throughout this guide

| Term | Meaning |
|------|---------|
| Agent | An LLM that can take actions (call tools) in a loop until a task is done |
| RAG | Retrieval-Augmented Generation — fetch relevant documents before generating a reply |
| RBAC | Role-Based Access Control — restrict what data each role can see |
| Embedding | A vector (list of numbers) that encodes semantic meaning of text |
| Vector store | A database optimised for similarity search over embeddings |
| Checkpointer | Persistent storage of graph state so history survives across turns |
| Interrupt | LangGraph mechanism to pause a graph and wait for human input |
| Tool call | The LLM requesting the host application to run a specific function |
| Pending write | A staged file change waiting for user confirmation before being applied |
| Hallucination | LLM producing plausible-sounding but fabricated information |
| TAO cycle | Think → Act → Observe — the agentic reasoning loop shown in the UI |
