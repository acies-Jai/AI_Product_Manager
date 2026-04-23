# 10 — Frequently Asked Questions

Questions a stakeholder, new engineer, or demo audience is likely to ask.

---

## Architecture & Design

**Q: Why build an AI PM assistant instead of using ChatGPT directly?**

ChatGPT has no knowledge of your organisation's documents, team, constraints, or priorities. Every
session starts blank. This system maintains a persistent knowledge base (the `inputs/` files),
enforces role-based access control so restricted data stays restricted, and has memory across a
conversation session via the LangGraph checkpointer. It's the difference between a generic PM
consultant and one who has read every document in your organisation.

---

**Q: Why LangGraph and not a plain Python for-loop?**

The hand-rolled for-loop approach was the original implementation and worked for simple cases.
LangGraph adds three things that became necessary:

1. **Conversation memory across turns** without manually managing a history list — the
   `operator.add` reducer on `PMState.history` accumulates turns automatically via the
   MemorySaver checkpointer keyed on `thread_id`.

2. **Human-in-the-loop confirmation** via `interrupt()` / `Command(resume=...)` — pausing
   mid-graph to wait for user confirmation before writing to a file, then resuming exactly where
   it left off, is trivial in LangGraph and complex to implement safely in a plain loop.

3. **Streaming to the UI** via `graph.stream(stream_mode="updates")` — each node's output is
   yielded as it completes, enabling the real-time Think/Act/Observe display. A plain loop returns
   only at the end.

---

**Q: Why Groq instead of OpenAI?**

Groq's LPU hardware generates tokens significantly faster than GPU-based providers. For an
interactive assistant, latency matters: a 3-second response feels snappy; a 15-second response
feels broken. Groq uses the OpenAI-compatible API format so the code would work with OpenAI,
Anthropic, or any other provider by changing `MODEL` in `core/client.py` and swapping the client.

---

**Q: Why ChromaDB instead of a proper database?**

For a POC with fewer than 1,000 documents, ChromaDB running in-process with local file
persistence is ideal: no server to manage, no network latency, no credentials. The `VectorStore`
class in `rag.py` wraps ChromaDB with a clean interface so the rest of the codebase doesn't
depend on ChromaDB-specific APIs. Migrating to Pinecone or pgvector means rewriting only `rag.py`.

---

**Q: What is the context window and why does it matter?**

The LLM processes the entire conversation in one pass on every call. "Context window" is the
maximum number of tokens (≈ words) it can process at once. Llama 3.3-70b has 128k tokens.
For this system, the context on each call contains: system prompt (~500 tokens), pre-retrieved
chunks (~800 tokens), conversation history (grows over session), current message, and any tool
results. Long sessions with many tool calls can approach this limit. The MemorySaver checkpointer
stores full history, but sending all of it on every call will eventually hit the limit. The
practical mitigation is summarising or truncating older history (not yet implemented).

---

## RAG & RBAC

**Q: How does the system know which documents to search?**

It doesn't pre-select documents — it runs a semantic search across all indexed chunks
simultaneously. When you ask "what are the engineering blockers?", the embedding of that question
is compared to the embeddings of all ~500 chunks in ChromaDB, and the 3–4 closest matches (by
cosine similarity) are returned, regardless of which file they came from.

---

**Q: What if two documents contradict each other?**

The LLM receives both as context and must reconcile them. The system prompt instructs it to cite
the source file and section when answering, so if `tech.md` says "3 engineers available" and
`product_context.md` says "team of 5", the model will cite both and may ask for clarification.
There is no automated conflict resolution — that's a human PM responsibility.

---

**Q: Can a user bypass the RBAC by selecting "Product Manager" from the dropdown?**

In this POC, yes — role selection is on the honour system. The technical controls (ChromaDB
metadata filtering, hallucination guards) work correctly regardless of which role is selected; the
weakness is that a malicious or curious user could simply self-elevate. In a production deployment,
the role would be derived from an authenticated identity (SSO token, JWT claim) and the dropdown
would be replaced by a role read from the auth context.

---

**Q: Why does the system return "This information is restricted" instead of just saying "I don't know"?**

"I don't know" is ambiguous — it could mean the information doesn't exist, or the model failed to
find it, or it's restricted. Saying "restricted" explicitly tells the user:
1. The information exists in the system
2. It's accessible to other roles
3. They should contact the relevant lead rather than assuming it's unknown

This is better UX and better security communication. It also makes role-based access visible,
which helps users understand why they're getting different responses than a colleague.

---

**Q: What happens when a document is indexed — how are the chunks stored?**

1. `load_inputs()` reads all `.md` files from `inputs/` into a dict of `{filename: content}`
2. `_chunk_document()` in `rag.py` splits each file on `\n## ` boundaries, creating one chunk
   per section with the section heading as metadata
3. Each chunk is assigned a classification level from `config/access_config.yaml`
4. ChromaDB's default embedding function converts each chunk's text into a 384-dim vector
5. Chunks, vectors, and metadata are stored in `.chroma/` (a local SQLite + binary files)
6. On subsequent searches, only the query is embedded at query time; chunk embeddings are cached

---

## The Agentic Loop

**Q: What is the TAO cycle display in the UI?**

TAO stands for Think → Act → Observe — the three phases of each agent iteration:
- **Think:** The LLM reasons about what to do next (shown as the intent classification and
  pre-fetch results)
- **Act:** The agent calls a tool (`search_context`, `send_email`, etc.)
- **Observe:** The tool result is shown as a preview

In the UI, this is rendered inside an `st.status()` expander that expands while the agent is
working and collapses with "✅ Response ready" when done. Each node in the LangGraph graph
produces an event that is rendered as a TAO step.

---

**Q: Why does the agent sometimes call `search_context` multiple times?**

The agent is reasoning about what it needs. First it might search "H1 FY26 roadmap initiatives"
and get back customer experience features. Then it searches "engineering capacity Q1" to check
feasibility. Then "growth metrics retention" to understand the business case. This multi-step
retrieval builds a richer context than a single query would, especially for complex questions that
span multiple departments. The system prompt encourages this: "You may call it multiple times with
different queries."

---

**Q: What happens if the Groq API returns an error mid-agent-loop?**

Two scenarios:

1. **`BadRequestError`** (malformed messages list): Caught explicitly. The handler strips all
   `tool` and `tool_calls` messages from the list and retries with a clean context. The reply
   may lack tool results but the conversation doesn't crash. Code: `core/graph.py` lines ~174–183.

2. **Network/timeout error**: Not currently caught — bubbles up to Streamlit as an exception and
   shows an error in the UI. In production, wrapping in `try/except` with a retry and exponential
   backoff would be the fix.

---

**Q: What is the "narration guard" and why is it needed?**

Some LLMs, when uncertain about how to use a tool, write the tool call as prose:
`"Let me search for the budget data..."` without actually calling the tool. Then they answer from
training data (hallucinate). The narration guard detects keywords like "let me search", "looking
up", "retrieving" in a response that has no actual tool calls, injects a correction (`"You
described a search but did not call the tool — call it now"`), and loops again. This forces the
model to actually use the structured tool call mechanism. Code: `core/graph.py` lines ~207–229.

---

## Document Updates

**Q: Can the agent modify any file or only specific sections?**

Currently only `## ` level-2 heading sections within `inputs/*.md` files. The
`propose_update_section` tool requires both a `filename` and a `heading` that must exactly match
an existing `## ` heading in the file. The regex replacement preserves the heading line and only
replaces the body text under it. Creating new files and deleting existing files are also
supported via `propose_create_file` and `propose_delete_file`.

---

**Q: What if the agent proposes a change to a section that doesn't exist in the file?**

`execute_write()` in `core/files.py` uses `re.search()` to verify the section exists before
calling `re.sub()`. If no match is found, it returns:
`"Section '## Heading' not found in filename.md — no changes made."` This message is returned to
the agent's context, which should then either call `read_file` to see the actual headings, or
tell the user the section wasn't found.

---

**Q: Why is there a "stale artifacts" banner after a document update?**

The six artefacts (Roadmap, RICE Score, etc.) are generated from the content of the `inputs/`
files at a specific point in time. If `tech.md` is updated to reflect new sprint capacity, the
Roadmap artefact no longer reflects that new reality — it was generated from the old data. The
stale banner is a reminder to regenerate before sharing artefacts with stakeholders. It's a
deliberate design choice: auto-regenerating artefacts on every update would consume LLM tokens
and time, often unnecessarily.

---

## Email

**Q: How does the agent know who to email?**

The agent is instructed to always call `search_context` first to look up an email address from
`inputs/employees.md` before calling `send_email`. The `employees.md` file contains each person's
name, role, email, and responsibilities. If the user asks to "notify the tech lead", the agent
searches for "tech lead email" and retrieves the address from the document.

---

**Q: What prevents the agent from emailing an external address?**

The `send_email` tool handler in `core/tools.py` validates every recipient against an allow-list
extracted from `employees.md` using a regex. Any address not found in that file is rejected with
an error message telling the agent to look up the correct address first. Since `employees.md`
only contains internal team addresses, external addresses cannot be sent to. This is enforced at
the tool execution layer — the LLM cannot bypass it through prompting.

---

**Q: What if Gmail credentials are not configured?**

Both `send_or_log()` (SMTP) and `read_inbox()` (IMAP) check for the `GMAIL_SENDER` and
`GMAIL_APP_PASSWORD` environment variables. If absent:
- `send_or_log()`: logs the email to `outputs/email_log.txt` with mode `[SIMULATED]`
- `read_inbox()`: returns `[{"error": "GMAIL_SENDER / GMAIL_APP_PASSWORD not set"}]`

The agent handles the `read_inbox` error gracefully — the error JSON is returned as the tool
result, and the agent tells the user inbox reading is unavailable. The application never crashes
due to missing email credentials.

---

## Extending & Operating

**Q: How do I add a new department's documents?**

1. Create `inputs/{department}.md` with `## ` headed sections
2. Add an entry to `config/access_config.yaml` under `document_classifications` with the
   appropriate level (`open`, `internal`, or `restricted`)
3. Add any key personnel to `inputs/employees.md`
4. In the Streamlit UI: click ↺ Reload Files, then 🔍 Index Documents
5. The agent can now answer questions about the new department immediately

No code changes are needed.

---

**Q: How do I change which roles can see restricted data?**

Edit `config/access_config.yaml` under `role_permissions`. Add or remove `restricted` from a
role's allowed levels list. Then restart the app (or trigger a re-index — ChromaDB reads the
classification at query time from the where filter, which is built from `allowed_levels()` which
reads the YAML). No code changes needed.

---

**Q: What does the MemorySaver checkpointer actually store, and what is lost on restart?**

`MemorySaver` stores the full `PMState` in a Python dict keyed by `(thread_id, checkpoint_id)`.
It lives in the process's memory — when the Streamlit server restarts, all conversation history
is lost. The next session starts with a fresh `thread_id` (new UUID) and empty history.

What persists across restarts (because it's on disk):
- `inputs/*.md` files
- `.chroma/` vector store data
- `outputs/*.md` artefact files
- `outputs/email_log.txt`
- `outputs/chat_log.txt`

To persist conversation history across restarts, replace `MemorySaver()` with
`SqliteSaver.from_conn_string("checkpoints.db")` in `core/graph.py`. One line change.

---

**Q: How is the RICE score calculated — does the model do the maths?**

Yes — the LLM is instructed to calculate `(Reach × Impact × Confidence%) ÷ Effort` and round to
one decimal place. This is arithmetic that LLMs perform reliably for round numbers. The model is
also instructed to sort rows by RICE Score descending before outputting the table. For a
production system where precision matters, you could parse the table, extract the four input
columns, and recalculate the score programmatically after generation.

---

**Q: Can the system handle multiple pending writes in one turn?**

Not currently. `PMState.pending_write` holds a single `dict | None`. If the agent calls two
`propose_*` tools in one turn, only `pending_writes[0]` is kept (see `_make_return()` in
`core/graph.py`). The second proposed change is silently dropped. In practice this rarely happens
because the system prompt instructs the agent to propose one change at a time. Fixing this
requires changing `pending_write` to `list[dict]` and updating the confirmation UI to process a
queue of confirmations.

---

**Q: What is the difference between `retrieve_context` (pre-fetch) and the `search_context` tool?**

`retrieve_context` is a **proactive, automatic** retrieval step that runs before the agent loop,
controlled by the graph. It runs for `search_query`, `file_edit`, and `email_request` intents —
3 results — and injects them as a supplementary system message. This gives the agent a head start.

`search_context` is a **reactive, on-demand** tool the agent calls *during* the loop when it
decides it needs more information. The agent chooses the query, the number of results, and when
to call it. The two work together: pre-fetch covers the obvious retrieval, in-loop search handles
follow-up queries or finer-grained lookups.
