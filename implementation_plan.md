# Implementation Plan — Remaining Features

Two features remain unimplemented as of 2026-04-23:
1. **RICE Scoring Framework** — prioritisation artifact with quantified scores per initiative
2. **System Documentation** — Q&A-ready explainer of the full system for demos and onboarding

---

## Feature 1: RICE Scoring Framework

### What it is
RICE = Reach × Impact × Confidence ÷ Effort. Each initiative gets four scores that produce a single
numeric priority rank, making trade-off discussions objective rather than opinion-driven.

### Where it lives in the app
A new **RICE Score** tab alongside the existing five artifact tabs. Rendered as a sortable markdown
table — highest score at top.

### Implementation steps

#### Step 1 — Add RICE to the artifact prompt (`core/artifacts.py`)
- Add `"===RICE_SCORE==="` to `_DELIMITERS` and `"rice_score"` to `_SECTIONS`
- Add the new section to `_ARTIFACT_PROMPT` with exact instructions:

```
===RICE_SCORE===
Markdown table with columns: Initiative | Reach (1–10) | Impact (1–3) | Confidence (%) | Effort (person-weeks) | RICE Score
RICE Score = (Reach × Impact × Confidence) ÷ Effort. Round to 1 decimal. Sort by RICE Score descending.
Initiatives must come from the Roadmap section above — do not invent new ones.
===END===
```

- Add a retrieval query `"initiative prioritisation effort reach impact confidence"` to `_ARTIFACT_QUERIES`

#### Step 2 — Parse the new section (`core/artifacts.py`)
- `_parse_response` already handles this generically once the delimiter and key are added — no extra parsing logic needed.
- Add `load_saved_artifacts()` coverage: the existing loop over `_SECTIONS` will pick up `rice_score.md` automatically.

#### Step 3 — Render in the UI (`app.py`)
- Add `"RICE Score"` to the `st.tabs(...)` list
- Add `"rice_score"` to the `keys` list
- No special renderer needed — plain `st.markdown(content)` renders the table correctly.

#### Step 4 — Include in notification email (`core/email_service.py`)
- `_artifact_email_body` already iterates over all keys in the artifacts dict using `LABELS`.
- Add `"rice_score": "RICE SCORE"` to the `LABELS` dict — email inclusion is automatic.

#### Step 5 — Update CLAUDE.md
- Add RICE to the artifact types table under "Artifact Generation".

### Acceptance criteria
- RICE Score tab appears after Impact Quadrant in the UI.
- Table has all five columns, sorted descending by RICE Score.
- Initiatives match those in the Roadmap tab (no hallucinated extras).
- Notification email includes the RICE table.

---

## Feature 2: System Documentation

### What it is
A single `SYSTEM_GUIDE.md` file written for two audiences:
- **Demo / Q&A** — explains what the system does, the flow, and the design decisions in plain language
- **Onboarding** — enough detail for a new team member to understand every layer without reading all code

### Where it lives
Root of the repo as `SYSTEM_GUIDE.md`. Not inside `inputs/` (it is not indexed into the vector store).

### Content outline (each section is a `##` heading)

1. **What this system does** — one-paragraph summary, the PM problem it solves
2. **System architecture** — the five layers: Input Files → RAG/RBAC → LangGraph Agent → Artifacts → Email
3. **Data flow diagram** (ASCII) — user message through the full graph and back
4. **LangGraph graph walkthrough** — each node (classify_intent, retrieve_context, generate_response, human_confirm), what it does, and why it exists
5. **Role-based access control** — the three classification levels, which roles can see what, how it is enforced in ChromaDB queries
6. **Tool system** — each of the 7 tools, when the agent calls them, the email allow-list guard
7. **Artifact generation** — the 7 retrieval queries, delimiter parsing, the 6 artifact types (including RICE after Feature 1)
8. **Email subsystem** — SMTP send, IMAP read, the `_artifact_email_body` builder, fallback logging
9. **Document update flow** — propose → interrupt → confirm/cancel → execute_write → reindex → stale flag
10. **Hallucination guards** — the three layers: STRICT RULE in system prompt, narration guard (continue loop), _should_deny_access intercept
11. **Known limitations** — no web search, no persistent auth, no test suite, hardcoded artifact queries
12. **Extending the system** — adding new input docs, roles, tools, artifact types, LLM model swap
13. **Frequently asked questions** — 10 Q&A pairs covering the most common demo questions

### Implementation steps

#### Step 1 — Write the ASCII data flow diagram
Trace a single chat message through the full system:
```
User types message
  → app.py: graph.stream(input_state)
    → classify_intent node: Groq call → intent label
    → retrieve_context node: VectorStore.search (role-filtered) → chunks
    → generate_response node: Groq agentic loop (up to 8 iterations)
        ↳ tool_calls → run_tool() → result appended to messages
        ↳ no tool_calls → reply returned
    → [if pending_write] → human_confirm node: interrupt() → wait
        ↳ Command(resume=True)  → execute_write → reindex
        ↳ Command(resume=False) → cancel
  → app.py: renders reply + TAO trace in st.status()
```

#### Step 2 — Write Q&A pairs
Cover: why LangGraph, why ChromaDB, how RBAC works, what happens if the model hallucinates, how to add a new department, why emails use an allow-list, how the Impact Quadrant differs from RICE, what the MemorySaver checkpointer does, how to test without real Gmail credentials, what "stale artifacts" means.

#### Step 3 — Write the file
Produce `SYSTEM_GUIDE.md` in the repo root. Approximately 600–900 words of prose plus diagrams and Q&A.

### Acceptance criteria
- Every major component has a prose explanation.
- The ASCII diagram is accurate end-to-end.
- All 10 Q&A pairs address questions a stakeholder or new developer would actually ask.
- No code is duplicated from source files — descriptions reference file and line ranges.

---

## Implementation order

| Step | Task | File(s) touched |
|------|------|----------------|
| 1 | Add RICE delimiter + query to artifact prompt | `core/artifacts.py` |
| 2 | Add RICE tab to Streamlit UI | `app.py` |
| 3 | Add RICE label to email body builder | `core/email_service.py` |
| 4 | Write `SYSTEM_GUIDE.md` | `SYSTEM_GUIDE.md` (new) |
| 5 | Update `CLAUDE.md` artifact table | `CLAUDE.md` |
