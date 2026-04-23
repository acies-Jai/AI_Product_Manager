# 11 — Frontend Developer Guide
### Everything you need to implement `frontend_plan.md`

This guide is written for someone who knows HTML/CSS/JS but is new to this project and to
Streamlit. It covers only what you need to touch to implement the redesign — nothing else.

---

## The one file you will edit: `app.py`

The entire UI is in a single file: `app.py` (365 lines). The backend does not change at all.
You will not touch `core/`, `rag.py`, or any config file.

Here is the exact structure of `app.py` top to bottom — know where each section is before
you start changing it:

```
Lines 1–18    imports
Lines 25–71   _render_quadrant() — the only existing render function
Lines 74–98   session state initialisation (runs once per browser session)
Lines 107–154 sidebar (with st.sidebar: block)
Lines 157–214 main area: header, role selector, artifact tabs
Lines 218–278 chat history renderer
Lines 280–364 chat input handler + TAO stream loop
```

---

## How Streamlit works — the one concept that trips everyone up

**Streamlit reruns the entire `app.py` from top to bottom on every user interaction.**

This means:
- There are no event listeners, no callbacks, no component lifecycle
- When a button is clicked, the script reruns and `st.button(...)` returns `True` *once*
- The only way to persist state across reruns is `st.session_state`
- `st.rerun()` manually triggers another full rerun (used after state mutations)

Practical consequence for the redesign: every HTML/CSS block you write gets re-executed and
re-rendered on every interaction. Keep rendering functions pure and fast.

---

## How to inject CSS

Streamlit has no stylesheet file. All custom CSS is injected via:

```python
st.markdown("""
<style>
  /* your CSS here */
</style>
""", unsafe_allow_html=True)
```

**Where to put it:** at the very top of `app.py`, right after `st.set_page_config(...)` on
line 20. It runs on every rerender, which is fine — browsers deduplicate `<style>` blocks.

**What you can and cannot target:**

Streamlit renders components inside shadow-like wrappers. Use browser DevTools to find the
actual CSS selectors. Key ones:

| What | Selector |
|------|---------|
| Sidebar container | `[data-testid="stSidebar"]` |
| Main content area | `.block-container` |
| Tab list | `.stTabs [data-baseweb="tab-list"]` |
| A single tab | `.stTabs [data-baseweb="tab"]` |
| Selected tab | `.stTabs [aria-selected="true"]` |
| Primary button | `.stButton > button[kind="primary"]` |
| Any button | `.stButton > button` |
| Chat message | `[data-testid="stChatMessage"]` |
| st.status expander | `[data-testid="stStatusWidget"]` |

**Limitation:** Streamlit aggressively scopes some components. If a CSS rule doesn't apply,
inspect the rendered DOM in DevTools and look for the actual element — it's often one wrapper
deeper than expected.

---

## How to render custom HTML

```python
st.markdown("<div style='color:red'>Hello</div>", unsafe_allow_html=True)
```

The `unsafe_allow_html=True` flag is required. Without it, Streamlit strips all HTML tags.
Inline styles are the most reliable approach because Streamlit's class names are auto-generated
and change between versions.

**Streamlit does not execute JavaScript.** `<script>` tags inside `st.markdown` are stripped.
If you need JS behaviour (animations, click handlers), use `st.components.v1.html()` instead —
this renders inside an iframe and can run JS.

---

## Session state — what's available to your render functions

These variables are available anywhere in `app.py` after line 91:

| Variable | Type | What it contains |
|----------|------|-----------------|
| `docs` | `dict[str, str]` | `{"tech": "# Tech...", "finance": "# Finance..."}` — all input files |
| `vs` | `VectorStore` | The ChromaDB wrapper; call `vs.count()` to get indexed chunk count |
| `artifacts` | `dict[str, str]` | Keys: `roadmap`, `key_focus_areas`, `requirements`, `success_metrics`, `impact_quadrant`, `rice_score`. Values: raw markdown strings from the LLM. |
| `st.session_state.messages` | `list[dict]` | Chat history — see structure below |
| `st.session_state.pending_write` | `dict \| None` | Staged file change — see structure below |
| `st.session_state.stale_artifacts` | `bool` | True when a document was edited and artifacts need regenerating |
| `role` | `str` | The currently selected role string from the selectbox |

---

## Exact data structures you'll render

### `artifacts` dict

```python
artifacts = {
    "roadmap": """| Now | Next | Later |
|-----|------|-------|
| 1-click reorder | Checkout redesign | Language search |
| Proactive ETA alerts | Real-time tracking | Personalised home |""",

    "key_focus_areas": """1. **Reduce checkout abandonment** — The install-to-order drop-off...
2. **Fix search 0-result rate** — Currently at 21%...""",

    "requirements": """## Requirements
- Users must be able to complete checkout in under 3 steps
...
## Scope
**In:** mobile app, web checkout
**Out:** dark store operations
...
## Final Specification
Acceptance criteria per requirement...""",

    "success_metrics": """| Initiative | Pre-launch Metric | Post-launch Metric | Owner |
|------------|-------------------|-------------------|-------|
| 1-click reorder | Reorder rate 18% | Reorder rate 28% | PM |
| Checkout redesign | Drop-off 42% | Drop-off 28% | PM / Design |""",

    "impact_quadrant": """--QUICK_WINS--
- Proactive ETA alerts
- Automated refunds for small orders
--MAJOR_BETS--
- Checkout flow redesign
- Personalised home screen
--LOW_HANGING--
- Push notification copy refresh
--DEPRIORITISE--
- Real-time inventory display
--END_QUADRANT--""",

    "rice_score": """| Initiative | Reach | Impact | Confidence | Effort | RICE Score |
|-----------|-------|--------|------------|--------|------------|
| 1-click reorder | 800 | 2 | 80% | 2 | 640.0 |
| Checkout redesign | 600 | 3 | 70% | 5 | 252.0 |"""
}
```

The values are **raw LLM output** — they roughly follow the formats above but the exact
whitespace, number of rows, and phrasing will vary each time artifacts are generated. Write
parsers defensively (use `.get()`, handle empty strings, strip whitespace).

---

### `st.session_state.messages` list

Each item is a dict with these keys:

```python
{
    "role": "user",           # or "assistant"
    "display": "**[Product Manager]** What is the budget?",  # markdown string shown in UI
    "tool_events": []         # only present on assistant messages
}
```

`tool_events` is a list of dicts, one per tool call the agent made:

```python
[
    {
        "type": "search",           # "search" | "email" | "inbox" | "write_staged" | tool_name
        "detail": "H1 FY26 budget", # query string, recipient email, or tool name
        "result_preview": "[finance / Budget...]\n## Budget..."  # first 300 chars of result
    },
    {
        "type": "email",
        "detail": "anirudh.shadipuram@aciesglobal.com",
        "result_preview": "sent to anirudh.shadipuram@aciesglobal.com"
    }
]
```

User messages always have `tool_events: []`. The user `display` string always starts with
`**[RoleName]** ` — you can split on `"] "` to separate the role label from the message text.

---

### `st.session_state.pending_write` dict

```python
{
    "tool": "propose_update_section",   # or "propose_create_file" | "propose_delete_file"
    "args": {
        "filename": "tech",             # stem only, no .md
        "heading": "Feasibility Notes", # exact ## heading text, no ##
        "new_content": "Updated text..."
    }
}
```

For `propose_create_file`: args are `{"filename": "...", "content": "..."}`.
For `propose_delete_file`: args are `{"filename": "..."}`.

When `pending_write` is not None, you must render the confirmation panel with Confirm / Cancel
buttons. Clicking Confirm calls `graph.invoke(Command(resume=True), _graph_config())`.

---

## The TAO stream loop — where the live thinking display happens

Lines 309–348 contain the streaming loop. This is the most complex part of `app.py`.

```python
with st.status("🤔 Thinking…", expanded=True) as tao_status:
    for event in graph.stream(input_state, _graph_config(), stream_mode="updates"):
        for node_name, updates in event.items():
```

`graph.stream()` yields one event dict per graph node as it completes. The three nodes that
produce UI-visible output:

| `node_name` | `updates` contains | What to render |
|------------|-------------------|----------------|
| `"classify_intent"` | `{"intent": "search_query"}` | The detected intent label |
| `"retrieve_context"` | `{"retrieved_context": [{"file":..., "section":...}]}` | Which files were pre-fetched |
| `"generate_response"` | `{"tool_events": [...], "reply": "...", "pending_write": ...}` | Each tool call as a step |

**Rule:** anything you call inside this `with st.status(...)` block is rendered inside the
collapsible expander. `st.write()`, `st.markdown()`, and `st.caption()` all work here.

---

## The artifact content parsers you need to write

The `frontend_plan.md` redesigns require parsing the raw markdown strings. Here are the exact
formats to parse:

### Roadmap table → Now / Next / Later columns

The roadmap is a markdown table. Split rows, skip the header and separator, then split each
row by `|` to get three cell values:

```python
def parse_roadmap(content: str) -> dict[str, list[str]]:
    result = {"now": [], "next": [], "later": []}
    lines = [l.strip() for l in content.strip().splitlines() if l.strip().startswith("|")]
    for i, line in enumerate(lines):
        if i == 0 or all(c in "-| :" for c in line.replace("|", "")):
            continue  # skip header and separator
        cells = [c.strip() for c in line.strip("| ").split("|")]
        if len(cells) >= 3:
            if cells[0]: result["now"].append(cells[0])
            if cells[1]: result["next"].append(cells[1])
            if cells[2]: result["later"].append(cells[2])
    return result
```

### RICE Score table → list of dicts

```python
def parse_rice_table(content: str) -> list[dict]:
    rows = []
    lines = [l.strip() for l in content.strip().splitlines() if l.strip().startswith("|")]
    for i, line in enumerate(lines):
        if i == 0 or all(c in "-| :" for c in line.replace("|", "")):
            continue
        cells = [c.strip() for c in line.strip("| ").split("|")]
        if len(cells) >= 6:
            try:
                rows.append({
                    "initiative": cells[0],
                    "reach": cells[1],
                    "impact": cells[2],
                    "confidence": cells[3],
                    "effort": cells[4],
                    "score": float(cells[5]) if cells[5].replace(".", "").isdigit() else 0,
                })
            except (ValueError, IndexError):
                continue
    return sorted(rows, key=lambda r: r["score"], reverse=True)
```

### Impact Quadrant (already parsed)

`parse_quadrant_sections(content)` is already imported and returns:
```python
{"quick_wins": "...", "major_bets": "...", "low_hanging": "...", "deprioritise": "..."}
```
Each value is the raw bullet text for that quadrant. This is called in `_render_quadrant()`.

---

## Plotly in Streamlit

Add `plotly` to `requirements.txt`, then:

```python
import plotly.graph_objects as go
fig = go.Figure(...)
st.plotly_chart(fig, use_container_width=True)
```

`use_container_width=True` makes the chart fill the column width. Set `config={"displayModeBar": False}` inside `st.plotly_chart()` to hide the Plotly toolbar for a cleaner look.

---

## Colour palette (from the existing theme)

| Token | Hex | Used for |
|-------|-----|---------|
| Brand purple | `#5E17EB` | Primary actions, headers, table headers |
| Light purple | `#7C3AED` | Gradient end, hover states |
| Background tint | `#F0EAFF` | Tab bar, status strip background |
| Dark sidebar | `#1A0533` | Sidebar background |
| Text dark | `#1A0533` | Body text |
| Green | `#10B981` | Success, Quick Wins, full access |
| Amber | `#F59E0B` | Warning, Next column, medium RICE |
| Red | `#EF4444` | Danger, Major Bets, low RICE |
| Blue | `#0EA5E9` | Tech role, search events |
| Pink | `#EC4899` | Design role |

---

## What NOT to change

- Do not touch anything in `core/`, `rag.py`, `server.py`, or `config/`
- Do not remove `st.session_state` initialisations (lines 76–89) — the rest of the app depends on them
- Do not change how `graph.stream()` is called (lines 310–346) — only change what is rendered inside the loop
- Do not remove the `Command(resume=True/False)` calls on lines 237 and 252 — these are how file writes are confirmed
- The `_render_quadrant()` function (lines 25–71) can be replaced entirely with a better version — it is self-contained

---

## Testing your changes

Start the app:
```bash
streamlit run app.py
```

For each UI change, verify it looks correct at three states:
1. **Not indexed:** `vs.count() == 0` — should show the empty onboarding state
2. **Indexed, no artifacts:** chunks > 0 but `artifacts == {}` — should show the generate prompt
3. **Fully loaded:** chunks > 0 and all 6 artifacts present — should show all tabs and chat

Use the FastAPI server to generate test data without going through the UI:
```bash
# In a separate terminal:
python -m uvicorn server:app --port 8502

# Index
curl -X POST http://localhost:8502/index

# Generate artifacts
curl -X POST http://localhost:8502/generate-artifacts

# Now the outputs/*.md files exist and the Streamlit app will load them
```
