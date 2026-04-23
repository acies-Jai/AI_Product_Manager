# 07 — Document Update Flow & Human-in-the-Loop

## Basics — why human-in-the-loop?

Agentic AI systems can take real-world actions: send emails, write files, delete records. Giving
an AI full autonomy over irreversible actions is dangerous — a misunderstood instruction could
delete the wrong file, send an email to the wrong person, or corrupt a document.

**Human-in-the-loop (HITL)** is the pattern of pausing agent execution at a critical decision
point and requiring a human to explicitly approve before the action is taken. The agent proposes;
the human confirms or cancels.

This is particularly important for write operations because:
- A wrong read is harmless (the model just got bad context)
- A wrong write has lasting consequences (file is modified or deleted)
- The user needs to understand exactly what will change before agreeing

---

## Going deeper — the propose/confirm pattern

The standard pattern for safe AI writes:

```
1. Agent reads the current document (to understand what it will change)
2. Agent calls a "propose" function with the intended change
3. Host application stores the proposal as "pending" — nothing written yet
4. UI shows the user: current state vs. proposed state (diff view)
5. User clicks Confirm → write is executed
   User clicks Cancel → proposal is discarded
6. If confirmed, the knowledge base is updated and downstream systems notified
```

The key design principle: **the agent never writes directly**. It can only *propose* a write.
The `execute_write` function exists in the host application and is gated behind user confirmation.

### What can be staged

Three types of write operations are supported:

| Operation | What it does | Reversibility |
|-----------|-------------|---------------|
| `propose_update_section` | Replaces the content of a `## Heading` section | Reversible (old content was readable before) |
| `propose_create_file` | Creates a new `.md` file in `inputs/` | Reversible (file can be deleted) |
| `propose_delete_file` | Deletes a file from `inputs/` | **Irreversible** — UI shows a red warning |

### The regex section replacement

`execute_write` uses a regex to find and replace a specific section:

```python
pattern = rf"(## {re.escape(heading)}\s*\n).*?(?=\n## |\Z)"
updated = re.sub(pattern, rf"\g<1>{new_content.strip()}", content, flags=re.DOTALL)
```

This replaces everything between the matched `## Heading` and the next `## Heading` (or end of
file). The heading line itself is preserved — only the body content changes.

### Post-confirmation pipeline

After a write is confirmed, three things happen automatically:
1. The file on disk is updated
2. `load_inputs()` is called to reload all input files into session state
3. `vs.index(fresh)` is called to re-chunk and re-embed the updated file

The vector store is now up to date. Any subsequent searches will reflect the new content.
A `stale_artifacts` flag is also set, showing a banner prompting the PM to regenerate artifacts.

---

## In this project

**Propose tools (staging):** `core/tools.py` — `_WRITE_TOOLS` set and the handler at lines
~198–200. When any `propose_*` tool is called:
```python
pending_writes.append({"tool": name, "args": args})
return "Change staged for user confirmation. Tell the user what you're proposing..."
```
The return value is injected back into the model's context so it knows the change is pending and
can describe it to the user.

**State field:** `core/graph.py` — `PMState.pending_write: dict | None`. Holds at most one
staged change. `pending_writes[0]` is taken if the list is non-empty.

**Routing to confirm:** `core/graph.py` — `route_after_generate` function, line ~288.
Returns `"human_confirm"` if `state.get("pending_write")` is truthy; otherwise returns `END`.

**interrupt() node:** `core/graph.py` — `human_confirm` node, lines ~267–284.
```python
confirmed = interrupt({"pending_write": state["pending_write"]})
```
Graph execution pauses here. LangGraph's MemorySaver preserves the full state so the graph can
resume exactly from this point.

**Diff preview:** `core/files.py` — `preview_write()`, lines ~35–58. For section updates,
reads the current file and extracts the current section content using the same regex as
`execute_write`. Returns a markdown-formatted `**Current:** / **Proposed:**` diff.

**Confirm panel in UI:** `app.py` lines ~222–257. Rendered at the top of the page whenever
`st.session_state.pending_write` is set. Shows the diff and two buttons:

```python
if st.button("✅ Confirm"):
    result = graph.invoke(Command(resume=True), _graph_config())
    fresh = load_inputs()
    vs.index(fresh)
    st.session_state.stale_artifacts = True
    ...

if st.button("❌ Cancel"):
    result = graph.invoke(Command(resume=False), _graph_config())
```

**Write execution:** `core/files.py` — `execute_write()`, lines ~23–32. Dispatches to the
appropriate private function based on `operation["tool"]`:
- `_exec_update_section()` — regex replace
- `_exec_create_file()` — `path.write_text()`
- `_exec_delete_file()` — `path.unlink()`

**Stale artifacts banner:** `app.py` lines ~182–192. When `stale_artifacts=True` and artifacts
exist, shows a yellow warning with a ↻ Regenerate button that re-runs `generate_artifacts()`.
