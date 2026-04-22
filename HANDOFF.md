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
