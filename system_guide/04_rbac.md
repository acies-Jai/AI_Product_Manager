# 04 — Role-Based Access Control (RBAC)

## Basics — what is RBAC?

Role-Based Access Control (RBAC) is a pattern where permissions are assigned to roles, and users
are assigned to roles. A user's access is determined entirely by their role, not by their
individual identity.

```
User → Role → Permissions → Data
Jai  → PM   → restricted  → sees everything
Anu  → Tech → internal    → sees open + internal, not restricted
```

In traditional software systems, RBAC controls access to APIs, database rows, or UI features. In
an AI system, RBAC controls **what context the LLM receives** — if restricted data never enters
the model's context, the model cannot reveal it, regardless of how the user phrases the question.

---

## Going deeper — RBAC in AI systems

### Why AI RBAC is different

In a conventional app, access control is binary: a user either has permission to read a record or
they don't, and the backend enforces this with a WHERE clause or a 403 response.

In an AI system, the challenge is that the LLM could receive context from multiple sources and
then *synthesise* information across them. A user asking "is the project on budget?" might cause
the model to combine a public timeline document with a restricted finance document. RBAC must
therefore operate at the **retrieval layer** — before the LLM ever sees the data.

### Classification levels

A common pattern is a hierarchy of classification levels:

```
open        — visible to everyone (public-facing, non-sensitive)
internal    — visible to employees but not customers or external parties
restricted  — visible only to specific privileged roles
```

Each document (or section within a document) is tagged with a level. Each role is given a list of
levels it is permitted to access. The vector store filters search results to only return chunks
whose classification is in the allowed set for the current role.

### The "no results" case

When a restricted document is searched with a role that doesn't have access, the search returns
zero results. This is correct behaviour — but the AI system must handle it gracefully. If the
model receives no results, it must be instructed to say "this information is not accessible for
your role" rather than guessing or hallucinating an answer.

This is harder than it sounds because LLMs have absorbed enormous amounts of financial and
business knowledge during training. A model asked "what is a typical quick commerce gross margin?"
will produce a confident, plausible number from training data even if search returned nothing.
Multiple defensive layers are needed (see `06_hallucination_guards.md`).

### Honour-system vs. enforced RBAC

In a POC without authentication, role selection is voluntary — a user picks their role from a
dropdown. This is "honour-system" RBAC: the access boundaries are defined and enforced at the
data layer, but a user could self-select a higher role.

In production, roles would be tied to authenticated identities (SSO tokens, JWT claims) and the
role would be derived server-side, not selected by the user.

---

## In this project

**Access configuration:** `config/access_config.yaml`. Defines:
- Per-file classification: which level each `inputs/*.md` file is tagged with
- Per-role allowed levels: which classification levels each role can access

Example structure:
```yaml
document_classifications:
  finance: restricted
  sales: restricted
  tech: internal
  product_context: internal
  customer_support: open
  employees: open

role_permissions:
  "Product Manager": [open, internal, restricted]
  "Finance": [open, internal, restricted]
  "Leadership": [open, internal, restricted]
  "Tech / Engineering": [open, internal]
  "Design": [open, internal]
  "Customer Experience (CS)": [open, internal]
  "Growth & Marketing": [open, internal]
  "Data Science / Analytics": [open, internal]
  "Operations": [open, internal]
  "Other": [open]
```

**`allowed_levels()` function:** `rag.py`. Takes a role string, returns the list of permitted
classification levels. Called before every VectorStore search.

**ChromaDB where filter:** `rag.py` — `VectorStore.search()`. The `where` clause:
```python
where={"classification": {"$in": allowed_levels(role)}}
```
ChromaDB applies this filter during vector search — restricted chunks are never returned for
roles without access.

**Chunk tagging:** `rag.py` — `_chunk_document()`. Every chunk gets:
```python
metadatas.append({
    "file": filename,
    "section": heading,
    "classification": classification
})
```
The classification is looked up from `access_config.yaml` at index time.

**Role selection in UI:** `app.py` lines ~163–168. `st.selectbox("Who are you?", [...])`.
The selected role is passed into every graph invocation as `state["role"]`.

**Access level indicator:** `app.py` lines ~170–176. After role selection, shows one of:
- 🔓 Full access (restricted included) — PM, Finance, Leadership
- 🔒 Internal access (restricted excluded)
- 🔒 Public only

**Role in agent context:** `core/graph.py` — the role string is passed to `run_tool()` for every
`search_context` call, ensuring all in-loop searches respect the same access level as the
pre-retrieval step.

**SEARCH_EMPTY response:** `core/tools.py` lines ~163–168. When `VectorStore.search()` returns
no results (because all matching chunks were filtered out), `run_tool` returns:
```
"SEARCH_EMPTY: No results found for this query under the current role.
This data may be classified above your access level.
Do NOT answer this question from general knowledge..."
```
This text is injected directly into the model's context as a tool result, priming it to respond
with a denial rather than a fabricated answer.
