# 06 — Hallucination Guards

## Basics — what is hallucination?

LLM **hallucination** is when a model produces text that is plausible-sounding but factually
incorrect or fabricated. The term comes from the model "seeing" something that isn't there — like
a person hallucinating.

Hallucination happens because:
- The model's training objective is to predict the next token, not to be accurate
- Confident, fluent text is rewarded during training regardless of factual grounding
- The model has no internal "I don't know" state — it always produces *something*

For a general-purpose assistant, a slightly wrong answer about historical events is annoying. For
a PM assistant with role-based access control, a hallucinated budget number cited as coming from
internal documents is a **security failure** — a restricted piece of information was effectively
fabricated for an unauthorised user.

---

## Going deeper — types of hallucination

### Factual hallucination
The model invents specific numbers, names, or dates that don't exist in any source document.
Example: "Our H1 FY26 budget is ₹15 Cr" when no such figure was in the context.

### Source hallucination
The model fabricates a citation. Example: "per budget_planning.md — Finance Notes" when no file
by that name exists in `inputs/`.

### Instruction bypass
The model has been told not to answer without search results, but it does anyway. The model
"narrates" a search ("I'll now search for budget data...") without actually calling the tool, then
answers from training data.

### The challenge of defending against instruction bypass

Instruction-following is learned behaviour, not a hard constraint. You cannot guarantee a model
will always follow a "STRICT RULE" system prompt instruction. Models fine-tuned heavily on
instruction-following do better, but no model is perfect. This is why **post-reply validation**
(checking the output) is just as important as **pre-reply instructions** (telling the model what
to do).

---

## Defence in depth — three layers

Effective hallucination prevention requires multiple overlapping defences. No single layer is
sufficient.

### Layer 1 — System prompt instruction (pre-reply)

The model is told explicitly:
```
STRICT RULE — never answer data questions from general knowledge:
- If search_context returns SEARCH_EMPTY, stop immediately.
- Do not guess, estimate, or fabricate figures.
- Tell the user clearly: "This information is restricted..."
```

This works well for compliant model responses but can be bypassed.

### Layer 2 — Narration guard (in-loop)

Some models write the tool call as prose instead of using the structured API:
```
"Let me search for the budget data... [searching for H1 FY26 budget]"
```
The loop detects this pattern and injects a correction before the next iteration:
```
"You described a search but did not call the search_context tool.
Do NOT narrate — call search_context now with the relevant query."
```
Then `continue` forces another loop iteration where the model (hopefully) calls the tool properly.

This guard prevents the model from narrating and then answering in the same turn without a real
search result.

### Layer 3 — Post-reply intercept (output validation)

Even if Layer 1 and Layer 2 fail, the final reply is checked before being returned to the user.
The check has two conditions — either triggers the intercept:

**Condition A** — searches were made but all returned SEARCH_EMPTY:
```python
def _all_searches_empty(tool_events):
    searches = [e for e in tool_events if e["type"] == "search"]
    if not searches:
        return False
    return all("SEARCH_EMPTY" in e.get("result_preview", "") for e in searches)
```

**Condition B** — no searches were made at all for a data-seeking intent:
```python
searches = [e for e in tool_events if e["type"] == "search"]
if not searches and intent in ("search_query",):
    return True
```

If either condition is true AND the reply contains financial/data patterns (₹, crore, budget,
revenue, cost, headcount, allocation), the reply is **replaced** with a denial message before
being shown to the user.

The regex pattern for financial data:
```python
_DATA_PATTERNS = re.compile(
    r"(₹\s*[\d,.]+\s*(cr|crore|lakh|l\b)|"
    r"\b\d+[\d,.]*\s*(cr|crore|%)\b|"
    r"budget|revenue|cost|headcount|allocation)",
    re.IGNORECASE,
)
```

---

## Limitations of these guards

- **Layer 3 has false positives:** If a legitimate reply discussing a public percentage (e.g., "90% of users prefer quick checkout") matches the pattern and zero searches were made for `general_chat` intent, the reply would incorrectly be suppressed. The intent check mitigates this but doesn't eliminate it.
- **The pattern list is not exhaustive:** A model could fabricate financial data using different phrasing not covered by `_DATA_PATTERNS`.
- **Layer 2 can loop without progress:** If the model keeps narrating after the correction, the loop burns iterations without getting a tool result.

These are acceptable trade-offs for a POC. Production systems would add: output scoring models,
fine-tuned refusal training, and structured output parsing for financial data specifically.

---

## In this project

**Layer 1 — STRICT RULE:** `core/graph.py` — `_AGENT_SYSTEM` constant, lines ~70–74.

**Layer 2 — Narration guard:** `core/graph.py` — `generate_response` node, lines ~207–229.
Triggered when `not tool_events` (no real tool calls yet) AND intent is data-seeking AND the
response text contains any narration keyword. Injects a correction message and `continue`s.

**Layer 3 — Post-reply intercept:** `core/graph.py` — `_should_deny_access()` lines ~320–332
and `_make_return()` lines ~335–360. Called at the very end of `generate_response` before
returning the reply dict.

**SEARCH_EMPTY message:** `core/tools.py` lines ~163–168. The exact text injected into the
model's context when a search returns no results due to RBAC filtering.

**Financial pattern regex:** `core/graph.py` lines ~312–317. `_DATA_PATTERNS` compiled once
at module load.

**Denial replacement message:** `core/graph.py` lines ~343–350. The fixed text that replaces a
suspected hallucinated reply:
```
"This information is restricted and not accessible for your current role.
The data you're asking about (budgets, financials, or restricted metrics)
is only available to roles with the appropriate access level
(Product Manager, Finance, or Leadership)."
```
