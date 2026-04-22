# Agent Handoff — Zepto PM Assistant

**Repo:** https://github.com/acies-Jai/AI_Product_Manager  
**Stack:** Python 3.11+, Streamlit, Groq (llama-3.3-70b-versatile), ChromaDB, dotenv  
**Run:** `streamlit run app.py` (requires `.env` with `GROQ_API_KEY`)

---

## What This Project Is

An agentic AI Product Manager assistant for Zepto (quick-commerce). It reads structured `.md` knowledge files from `inputs/`, answers questions via RAG + tool-calling, generates PM artifacts (roadmap, requirements, success metrics, impact quadrant), and can propose edits to the input files with a human-confirm step before writing.

---

## Current Codebase Structure

```
app.py                  — Streamlit UI (sole entry point)
agent.py                — shim: from core import *
rag.py                  — ChromaDB vector store with RBAC metadata filtering
core/
  __init__.py           — re-exports all public functions
  agent.py              — agentic loop (run_agent, log_message)
  artifacts.py          — artifact generation + quadrant parsing
  client.py             — Groq client, MODEL constant, path constants
  email_service.py      — SMTP send or file log fallback
  files.py              — load_inputs, execute_write, preview_write, read_file
  tools.py              — TOOLS list (6 tools) + run_tool dispatcher
inputs/
  product_context.md    — product charter, customer problems, OKRs
  tech.md               — engineering feasibility, constraints, team capacity
  finance.md            — budget, cost estimates (restricted)
  sales.md              — revenue, GMV data (restricted)
  employees.md          — team directory with emails
  customer_support.md   — ticket themes, CSAT data
config/
  access_config.yaml    — document classifications + role permissions
  email_config.yaml     — email trigger → recipient mappings
outputs/                — generated artifacts + logs (gitignored)
.env                    — GROQ_API_KEY (gitignored, never commit)
.env.example            — template
```

---

## Demo Readiness Checklist

These are the quickest path to a working end-to-end demo. In order:

| # | Task | Effort | Where |
|---|------|--------|-------|
| 1 | Rotate the exposed `GROQ_API_KEY` (see Environment Setup below) | 5 min | console.groq.com |
| 2 | Fix the text tool call regex (see Known Bug below) | 5 min | `core/agent.py:17` |
| 3 | Set `GMAIL_SENDER` + `GMAIL_APP_PASSWORD` in `.env` | 5 min | Google Account → Security → App Passwords |
| 4 | Replace fake `@zepto.com` recipients with real addresses | 5 min | `config/email_config.yaml` + `inputs/employees.md` |
| 5 | Enable IMAP in Gmail settings + add `read_inbox` tool (see Inbox Reading below) | 2–3 hrs | `core/email_service.py`, `core/tools.py` |

Steps 1–4 unlock real email sending with zero code changes. Step 5 closes the loop so the agent can read replies.

---

## Known Bug — Text Tool Call Fallback Is Incomplete

**Symptom:** The model (llama-3.3-70b-versatile) sometimes outputs tool calls as plain text instead of structured API calls. Example of what the model produces:

```
To find this year's revenue, I'll need to search for the relevant document.

Let me search for the revenue data using the search_context tool.

-search_context: "revenue data" AND "this year"

(Please wait while I retrieve the data)
```

The agent returns this monologue verbatim as the final answer — no search is performed, no real answer given.

**Root cause:** `core/agent.py:_parse_text_tool_call()` only matches the `=search_context:` prefix pattern (equals sign). The model is also producing `-search_context:` (dash prefix) and potentially other variants. The regex on line 17 is:

```python
m = re.search(r'=(\w+):\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
```

This misses the dash variant entirely.

**Fix needed:** Broaden the regex to catch multiple prefix styles. Replace line 17 in `core/agent.py` with:

```python
m = re.search(r'[-=](\w+):\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
```

Additionally, the function only handles `search_context`. If the model writes other tools as plain text (e.g. `-send_email:`, `-read_file:`), those are also silently dropped. Consider either:
- Expanding the parser to handle all 6 tools, or
- Moving to LangGraph (see migration plan below) which eliminates this problem entirely by using structured message passing.

---

## Email Inbox Reading

No inbox reading exists in the codebase. Adding it as a `read_inbox` tool closes the full communication loop for the demo: agent sends → stakeholder replies → agent reads and acts.

### Approach: IMAP (recommended for POC)

Uses `imaplib` + `email` from the Python stdlib. No new packages. Reuses the same Gmail App Password already in `.env`.

**Prerequisites (one-time):** In Gmail settings → See All Settings → Forwarding and POP/IMAP → Enable IMAP.

### Implementation

**1. Add `read_inbox()` to `core/email_service.py`:**

```python
import imaplib, email as emaillib
from email.header import decode_header

def read_inbox(query: str = "ALL", max_results: int = 5) -> list[dict]:
    """
    Fetch recent emails matching query. query is an IMAP search string,
    e.g. 'FROM "someone@example.com"' or 'SUBJECT "roadmap"'.
    Returns list of {sender, subject, date, body_snippet}.
    """
    sender = os.getenv("GMAIL_SENDER", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not (sender and password):
        return [{"error": "GMAIL_SENDER / GMAIL_APP_PASSWORD not set"}]

    with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
        mail.login(sender, password)
        mail.select("inbox")
        _, uids = mail.search(None, query)
        uid_list = uids[0].split()[-max_results:]  # most recent N

        results = []
        for uid in reversed(uid_list):
            _, data = mail.fetch(uid, "(RFC822)")
            msg = emaillib.message_from_bytes(data[0][1])
            subject, enc = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(enc or "utf-8", errors="replace")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")
            results.append({
                "sender": msg.get("From"),
                "subject": subject,
                "date": msg.get("Date"),
                "body_snippet": body[:500].strip(),
            })
    return results
```

**2. Add the tool definition to `core/tools.py` `TOOLS` list:**

```python
{
    "type": "function",
    "function": {
        "name": "read_inbox",
        "description": (
            "Read recent emails from the Gmail inbox. Use an IMAP search string "
            "to filter by sender, subject, or date. Returns sender, subject, date, "
            "and a 500-char body snippet for each matched email."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "IMAP search string, e.g. 'FROM \"boss@example.com\"' or 'SUBJECT \"roadmap\" SINCE 01-Jan-2025'. Use 'ALL' for most recent.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of emails to return (default 5).",
                },
            },
            "required": ["query"],
        },
    },
}
```

**3. Add the handler in `run_tool()` in `core/tools.py`:**

```python
elif name == "read_inbox":
    results = read_inbox(
        query=args.get("query", "ALL"),
        max_results=args.get("max_results", 5),
    )
    return json.dumps(results, ensure_ascii=False)
```

**4. Update the system prompt in `core/agent.py`** to mention `read_inbox` so the model knows when to use it.

### Limitations of IMAP approach

- No threading/conversation view — fetches individual messages
- IMAP search is basic; no full-text body search (only headers)
- Long-term, the Gmail API with OAuth2 is the right path (supports search, threading, labels, drafts) but requires a GCP project and OAuth flow

### Where this fits in the migration phases

This is a self-contained addition to the current codebase (no LangGraph needed). In the LangGraph migration, `read_inbox` becomes a tool available to the Communication Agent in Phase 3.

---

## LangGraph Migration Plan

The current hand-rolled loop in `core/agent.py` is a `for` loop with `if/else` branching. Every new capability makes it harder to reason about. LangGraph replaces it with an explicit state machine.

### State Schema

```python
from typing import TypedDict

class PMState(TypedDict):
    user_message: str
    role: str
    history: list[dict]
    retrieved_context: list[dict]   # chunks from RAG
    intent: str                     # classified intent
    tool_events: list[dict]
    pending_write: dict | None
    artifacts: dict[str, str]
    reply: str
    emails_sent: list[str]
    inbox_summary: list[dict]        # results from read_inbox tool
```

### Graph Nodes

| Node | Responsibility |
|---|---|
| `classify_intent` | Labels intent: `search_query`, `file_edit`, `artifact_request`, `email_request`, `general_chat` |
| `retrieve_context` | Calls `rag.VectorStore.search()`, fills `retrieved_context` |
| `generate_response` | Calls Groq with context, writes `reply` |
| `stage_file_edit` | Calls propose_* tools, fills `pending_write` |
| `send_notification` | Calls `core/email_service.py`, fills `emails_sent` |
| `generate_artifacts` | Calls `core/artifacts.py` pipeline |
| `human_confirm` | LangGraph interrupt — pauses graph for UI confirm/cancel |

### Graph Routing

```
START → classify_intent
  ├── search_query / general_chat → retrieve_context → generate_response → END
  ├── file_edit                  → stage_file_edit → human_confirm → END
  ├── email_request              → retrieve_context → send_notification → generate_response → END
  └── artifact_request           → generate_artifacts → send_notification → END
```

`human_confirm` uses `interrupt_before=["human_confirm"]` — LangGraph serialises state to disk and resumes when the user clicks Confirm in the UI. This replaces the current `st.session_state.pending_write` + `st.rerun()` hack.

### New File: `core/graph.py`

This is where the `StateGraph` definition, node functions, and edge conditions live. All existing `core/` modules stay unchanged — nodes import and call them.

### Changes to Existing Files

- **`core/agent.py`** — replaced by the graph in `core/graph.py`; keep `log_message` here
- **`core/client.py`** — add `langchain_groq.ChatGroq` alongside raw Groq client
- **`app.py`** — replace `run_agent()` call with `graph.invoke(state)` or `graph.stream(state)`; pending_write confirmation uses `graph.update_state()` to resume after interrupt
- **`core/__init__.py`** — export `run_graph` instead of (or alongside) `run_agent`

### Implementation Phases

**Phase 1 — Replace the loop**
- `pip install langgraph langchain-groq`
- Define `PMState`
- Migrate `core/agent.py` into `classify_intent → retrieve_context → generate_response` nodes
- Wire `human_confirm` interrupt for file writes

**Phase 2 — Specialist nodes**
- Add `generate_artifacts`, `send_notification`, `stage_file_edit` as dedicated nodes
- Conditional routing from `classify_intent`
- LangGraph checkpointing (SQLite) so state survives Streamlit reruns
- Add `read_inbox` to `send_notification` node (see Email Inbox Reading above) and expose `inbox_summary` in `PMState`

**Phase 3 — Multi-agent subgraphs**
- Split into: Research Agent, Document Agent, Communication Agent, Artifact Agent
- Wire via Orchestrator subgraph
- Add Tavily/Serper web search tool to Research Agent
- Add CSV upload + pandas analytics to a new Analytics Agent

**Phase 4 — Expanded PM task range**
- OKR/KPI generation node (from roadmap)
- PRD auto-draft node (from requirements artifact)
- Sprint planning node (uses `tech.md` capacity data)
- Weekly digest cron trigger → Communication Agent
- Risk register node (per-initiative risk + mitigation)
- Competitive analysis node (web search → structured matrix)

---

## Wider PM Task Catalogue (per node/subgraph)

**Discovery & Research**
- Competitive analysis via web search → competitor matrix
- Market sizing from public data
- Customer feedback synthesis from uploaded transcripts
- Tech feasibility check against `tech.md`

**Planning**
- OKR/KPI generation from roadmap
- Sprint planning with story point assignment
- Dependency mapping across initiatives
- Risk register with mitigations

**Stakeholder Communication**
- Auto-draft PRDs from requirements artifacts
- Executive summaries for leadership
- Changelog entries when artifacts update
- Stakeholder RACI matrix from `employees.md`

**Execution Tracking**
- Accept status updates via chat → update `tech.md` progress section
- Flag at-risk milestones
- Weekly digest email to stakeholders

**Team Management**
- Onboarding plans for new hires
- Performance review prompts for direct reports
- Workload distribution from team capacity data

---

## Environment Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
streamlit run app.py
```

**GROQ_API_KEY** — get from https://console.groq.com. The key in the original commit was exposed and must be rotated before use.

Optional email vars in `.env`:
```
GMAIL_SENDER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```
Without these, emails are logged to `outputs/email_log.txt` instead of sending.
