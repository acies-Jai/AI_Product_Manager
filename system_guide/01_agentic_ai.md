# 01 — Agentic AI

## Basics — what makes AI "agentic"?

A standard LLM call is stateless: you send a prompt, you get a reply, done. The model has no memory
of previous calls and takes no action beyond generating text.

An **agent** breaks that pattern. An agent is an LLM that:
1. Receives a goal, not just a question
2. Decides what action to take next (call a tool, search, write, send)
3. Executes that action and observes the result
4. Feeds the result back into its context and decides the next step
5. Repeats until the goal is achieved or a limit is hit

This loop — **Think → Act → Observe** — is sometimes called the ReAct pattern (Reasoning + Acting).

```
Goal given
  │
  ▼
┌──────────────────┐
│  THINK           │  ← LLM reasons about what to do next
│  (Groq call)     │
└────────┬─────────┘
         │ decides: call tool X with args Y
         ▼
┌──────────────────┐
│  ACT             │  ← host application runs the tool
│  (run_tool)      │
└────────┬─────────┘
         │ result returned
         ▼
┌──────────────────┐
│  OBSERVE         │  ← result appended to context
│  (messages list) │
└────────┬─────────┘
         │
         └──► loop back to THINK, or exit if done
```

The key insight: the LLM doesn't execute code directly. It *requests* actions by outputting
structured data (tool calls), and the host application executes them and feeds results back.

---

## Going deeper — tool calling

Tool calling (also called function calling) is the mechanism by which an LLM requests an action.
Instead of returning plain text, the model can return a structured `tool_calls` object:

```json
{
  "tool_calls": [{
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "search_context",
      "arguments": "{\"query\": \"engineering sprint capacity\"}"
    }
  }]
}
```

The host application:
1. Parses this object
2. Looks up the function by name
3. Executes it with the provided arguments
4. Appends the result as a `tool` role message:

```json
{"role": "tool", "tool_call_id": "call_abc123", "content": "Sprint 23: 6 engineers, 3 busy..."}
```

5. Calls the LLM again with the full updated context

The LLM never actually calls any function — it just outputs a request. This means the host
application has full control over what actually runs. This is also where safety controls live.

### Tool definitions

Before the first LLM call, the host sends a list of available tools as part of the API request:

```python
tools=[{
    "type": "function",
    "function": {
        "name": "search_context",
        "description": "Semantically search the organisation's documents...",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "n_results": {"type": "integer"}
            },
            "required": ["query"]
        }
    }
}]
```

The description is critical — it is part of the prompt. A good description tells the model *when*
and *why* to call the tool, not just what it does.

### Iteration limit

Agentic loops need a hard stop. Without one, a confused model can loop indefinitely. The standard
pattern is a `for _ in range(N):` loop that breaks when the model returns a final text reply.
If the limit is hit, the agent returns a fallback message like "Reached iteration limit".

---

## Multi-tool turns

A capable model can request multiple tools in a single turn. Each tool call in the `tool_calls`
list should be executed and its result appended before the next LLM call. This allows the model
to, for example, search three different queries in parallel and then synthesise the results.

The model can also call the same tool multiple times with different arguments across iterations,
refining its search query based on what the first search returned.

---

## The "text tool call" problem

Models trained on code have a learned behaviour: when uncertain about structured output, they fall
back to writing the tool call as plain text. For example:

```
search_context: "engineering sprint capacity"
```

This is the model *intending* to call a tool but producing prose instead of a structured API call.
Without a fallback handler, this silently fails — the model gets no search result and may then
answer from general knowledge (hallucinate).

The correct fix is a regex parser that detects this pattern and manually dispatches the tool,
then feeds the result back before requesting the final reply.

---

## In this project

**Agentic loop:** `core/graph.py` — `generate_response` node, lines ~140–265. The loop runs
`for _ in range(8):`, calling Groq with `tools=TOOLS, tool_choice="auto"` each iteration.

**Tool dispatch:** `core/tools.py` — `run_tool()` function. Handles all 7 tools. Called from
both the structured tool call path and the plain-text fallback path.

**Text tool call fallback:** `core/graph.py` — `_parse_text_tool_call()`, lines ~79–102.
Uses regex `rf'(?:[-=])?({_KNOWN_TOOLS}):\s*["\']?(.+?)["\']?\s*$'` to detect plain-text tool
calls the model writes when it doesn't use the structured API.

**Iteration limit:** `core/graph.py` line ~264. Returns "Reached iteration limit" if 8
iterations complete without a final reply.

**TAO display in UI:** `app.py` lines ~306–345. Each node update streamed via `graph.stream()`
is rendered inside `st.status()` so the user sees Think/Act/Observe in real time.

**Tool definitions:** `core/tools.py` — `TOOLS` list, lines ~18–148. Each dict has `name`,
`description`, and `parameters` following the OpenAI-compatible function calling schema.
