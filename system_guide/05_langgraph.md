# 05 — LangGraph: State Machines for AI Agents

## Basics — what is LangGraph?

LangGraph is a library for building stateful, multi-step AI applications as directed graphs.
Before LangGraph, most agentic AI was built as a plain for-loop: call LLM, check for tool calls,
execute tools, repeat. This works for simple agents but becomes hard to manage as complexity grows:
- How do you pause execution and wait for a human to confirm an action?
- How do you route different types of requests through different processing paths?
- How do you persist conversation history across separate HTTP requests?
- How do you stream intermediate results to the UI while the agent is still thinking?

LangGraph models the agent as a directed graph where **nodes are processing steps** and **edges
are transitions between them**. State flows through the graph, each node transforming it.

---

## Going deeper

### Core concepts

**StateGraph:** The graph definition. You add nodes and edges, then `compile()` it into a
runnable. The compiled graph handles state management, checkpointing, and streaming.

**State (TypedDict):** A typed dictionary that carries all data through the graph. Each node
receives the current state and returns a partial update (a dict with only the fields it changed).
LangGraph merges the update into the state.

**Nodes:** Python functions with signature `(state: StateType) -> dict`. They read from state,
do work, and return a partial update.

**Edges:** Connections between nodes. Two types:
- **Fixed edges:** `builder.add_edge(A, B)` — always go from A to B
- **Conditional edges:** `builder.add_conditional_edges(A, router_fn, {label: node, ...})`
  The `router_fn` returns a label based on the current state, determining which node to visit next.

**START / END:** Built-in nodes marking entry and exit points.

### Reducers

By default, returning `{"field": new_value}` from a node replaces the field in state. But some
fields should *accumulate* rather than replace. LangGraph supports this via **reducers**:

```python
from typing import Annotated
import operator

class MyState(TypedDict):
    messages: Annotated[list[dict], operator.add]  # each update appends, not replaces
    current_result: str                              # each update replaces
```

`operator.add` on a list means `state["messages"] + returned_list`. This lets different nodes
append their contributions without knowing about each other.

### Checkpointers

A checkpointer persists the full graph state after each node completes. This enables:
1. **Multi-turn memory:** State from turn 1 is loaded automatically at the start of turn 2
2. **Interrupt/resume:** The graph can pause mid-execution and be resumed later
3. **Fault tolerance:** A crash mid-graph can be retried from the last checkpoint

Checkpointers are keyed on a `thread_id`. All invocations with the same `thread_id` share the
same state history.

```python
from langgraph.checkpoint.memory import MemorySaver
graph = builder.compile(checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "user-session-123"}}
result = graph.invoke(state, config)  # turn 1
result = graph.invoke(new_state, config)  # turn 2 — picks up where turn 1 left off
```

Available checkpointers:
- `MemorySaver` — in-process dict, lost on restart. Good for development.
- `SqliteSaver` — persists to a SQLite file. Good for single-server production.
- `PostgresSaver` — persists to Postgres. Good for multi-server production.

### `interrupt()` and `Command`

`interrupt()` is LangGraph's mechanism for **human-in-the-loop**. When called inside a node, it
immediately pauses graph execution and returns control to the caller. The caller can then display
something to the user, collect their input, and resume the graph.

```python
from langgraph.types import interrupt, Command

def human_confirm(state):
    user_decision = interrupt({"data_to_show": state["pending_write"]})
    # execution pauses here — the caller gets the interrupt payload
    # later, graph.invoke(Command(resume=True), config) resumes from here
    if user_decision:
        return {"result": "confirmed"}
    return {"result": "cancelled"}
```

Resume with `Command`:
```python
# Resume with True (confirm)
graph.invoke(Command(resume=True), config)

# Resume with False (cancel)
graph.invoke(Command(resume=False), config)
```

### Streaming

`graph.stream(state, config, stream_mode="updates")` yields events as each node completes.
Each event is a dict: `{node_name: state_updates_from_that_node}`.

This lets the UI render partial results progressively:
- After `classify_intent` completes → show the detected intent
- After `retrieve_context` completes → show which documents were fetched
- After each tool call in `generate_response` → show the tool call and result preview
- After final reply → show the full response

---

## Graph structure in this project

```
START
  │
  ▼
classify_intent ──────────────────────────────────────────►
  │
  ▼
retrieve_context ─────────────────────────────────────────►
  │
  ▼
generate_response
  │
  ├─── pending_write is None ──────────────────────────► END
  │
  └─── pending_write is set ──────────────────────────►
                                                        human_confirm
                                                          │
                                                          ▼
                                                         END
```

### In this project — file references

**Graph definition:** `core/graph.py` — `build_graph(vector_store)` factory function,
lines ~107–309. Returns a compiled `StateGraph`.

**PMState:** `core/graph.py` lines ~19–27.
```python
class PMState(TypedDict):
    user_message: str
    role: str
    history: Annotated[list[dict], operator.add]  # accumulates via reducer
    retrieved_context: list[dict]                  # replaced each turn
    tool_events: list[dict]                        # replaced each turn
    pending_write: dict | None
    reply: str
    intent: str
```
`history` uses `operator.add` so every turn appends `[user_msg, assistant_reply]` without
any node needing to manually manage the history list.

**Node registration:** `core/graph.py` lines ~293–297.
```python
builder.add_node("classify_intent", classify_intent)
builder.add_node("retrieve_context", retrieve_context)
builder.add_node("generate_response", generate_response)
builder.add_node("human_confirm", human_confirm)
```

**Conditional routing:** `core/graph.py` lines ~302–306.
```python
builder.add_conditional_edges(
    "generate_response",
    route_after_generate,          # returns "human_confirm" or END
    {"human_confirm": "human_confirm", END: END},
)
```
`route_after_generate` checks `state.get("pending_write")` — if a file change was staged, route
to `human_confirm`; otherwise end.

**Checkpointer:** `core/graph.py` line ~309.
```python
return builder.compile(checkpointer=MemorySaver())
```
`MemorySaver` is used (in-memory, lost on restart). Migrating to `SqliteSaver` is a one-line change.

**Thread ID:** `app.py` lines ~88, 101. A UUID is generated once per session:
```python
st.session_state.thread_id = str(uuid.uuid4())
```
Passed to every `graph.stream()` / `graph.invoke()` call via `_graph_config()`.

**interrupt() usage:** `core/graph.py` — `human_confirm` node, lines ~267–284.
```python
confirmed = interrupt({"pending_write": state["pending_write"]})
```
Execution pauses here. `app.py` then renders the confirmation UI. When the user clicks Confirm or
Cancel, `graph.invoke(Command(resume=True/False), _graph_config())` resumes from this exact line.

**Streaming in UI:** `app.py` lines ~307–345. The `for event in graph.stream(...)` loop
processes updates from each node and renders them in a `st.status()` expander.
