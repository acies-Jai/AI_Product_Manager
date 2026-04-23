# Frontend Redesign Plan

Current state: functional Streamlit layout with basic markdown rendering and minimal custom
styling. The purple theme exists in config.toml but nothing beyond that.

Goal: a polished, demo-ready product that looks like a real internal tool — not a notebook.

All of this is achievable inside Streamlit using custom CSS injection, Plotly charts, and
`unsafe_allow_html=True`. No framework migration needed.

---

## Priority tiers

| Tier | Impact | Effort | What |
|------|--------|--------|------|
| 1 | Very high | Low | Global CSS, header, role selector, sidebar |
| 2 | High | Medium | Roadmap cards, RICE bar chart, chat bubbles |
| 3 | High | Medium | Success metrics table, TAO trace redesign |
| 4 | Medium | Medium | Animated states, status bar, empty states |
| 5 | Low | High | React migration (out of scope for now) |

---

## Tier 1 — Global CSS & Layout Foundation

### 1a. Global stylesheet injection

Inject once at the top of `app.py` via `st.markdown(..., unsafe_allow_html=True)`. This one block
transforms the entire look:

```python
st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px; }

/* Tabs — pill style */
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: #F0EAFF; padding: 6px; border-radius: 12px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 6px 18px; font-weight: 500; color: #5E17EB; }
.stTabs [aria-selected="true"] { background: #5E17EB !important; color: white !important; }

/* Buttons */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #5E17EB, #7C3AED);
    border: none; border-radius: 8px; font-weight: 600;
    box-shadow: 0 2px 8px rgba(94,23,235,0.3);
}
.stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(94,23,235,0.4); }

/* Sidebar */
[data-testid="stSidebar"] { background: #1A0533; }
[data-testid="stSidebar"] * { color: #E5D9FF !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px; color: white !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.15); }

/* Cards */
.pm-card {
    background: white; border-radius: 12px; padding: 20px;
    border: 1px solid #EDE9FF; box-shadow: 0 2px 8px rgba(94,23,235,0.06);
}

/* Chat bubbles */
[data-testid="stChatMessage"] { border-radius: 12px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)
```

**File:** `app.py` — insert right after `st.set_page_config()`

---

### 1b. Hero header

Replace the plain `<h1>` with a branded banner:

```python
st.markdown("""
<div style="
    background: linear-gradient(135deg, #5E17EB 0%, #7C3AED 60%, #9F67FA 100%);
    border-radius: 16px; padding: 28px 36px; margin-bottom: 20px;
    display: flex; justify-content: space-between; align-items: center;
">
    <div>
        <div style="color:rgba(255,255,255,0.7); font-size:12px; font-weight:600;
                    letter-spacing:2px; text-transform:uppercase; margin-bottom:4px;">
            ⚡ ZEPTO — PM INTELLIGENCE LAYER
        </div>
        <div style="color:white; font-size:26px; font-weight:800; line-height:1.2;">
            Product Manager Assistant
        </div>
        <div style="color:rgba(255,255,255,0.65); font-size:13px; margin-top:6px;">
            Charter: Customer App &amp; Checkout Experience
        </div>
    </div>
    <div style="text-align:right;">
        <div style="background:rgba(255,255,255,0.15); border-radius:20px; padding:8px 16px;
                    color:white; font-size:12px; font-weight:600;">
            {chunk_count} chunks indexed
        </div>
    </div>
</div>
""".format(chunk_count=vs.count()), unsafe_allow_html=True)
```

---

### 1c. Role selector with per-role colour badges

Replace the plain `st.selectbox` + `st.caption` with a selectbox followed by an inline
role badge that changes colour by access level:

```python
ROLE_CONFIG = {
    "Product Manager":             ("#5E17EB", "👤", "Full access"),
    "Finance":                     ("#10B981", "💰", "Full access"),
    "Leadership":                  ("#F59E0B", "🏆", "Full access"),
    "Tech / Engineering":          ("#0EA5E9", "⚙️",  "Internal access"),
    "Design":                      ("#EC4899", "🎨", "Internal access"),
    "Growth & Marketing":          ("#F97316", "📈", "Internal access"),
    "Customer Experience (CS)":    ("#14B8A6", "🎧", "Internal access"),
    "Data Science / Analytics":    ("#8B5CF6", "📊", "Internal access"),
    "Operations":                  ("#6B7280", "🏭", "Internal access"),
    "Other":                       ("#9CA3AF", "👥", "Public only"),
}

color, icon, access_label = ROLE_CONFIG.get(role, ("#9CA3AF", "👥", "Public only"))
st.markdown(f"""
<div style="display:flex; align-items:center; gap:10px; margin-top:4px; margin-bottom:16px;">
    <span style="background:{color}20; color:{color}; border:1px solid {color}40;
                 border-radius:20px; padding:4px 14px; font-size:13px; font-weight:600;">
        {icon} {role}
    </span>
    <span style="color:#888; font-size:12px;">{access_label}</span>
</div>
""", unsafe_allow_html=True)
```

---

### 1d. Sidebar redesign

Current sidebar has plain buttons and text. Replace with:
- Dark sidebar background (already set in CSS above: `#1A0533`)
- Section labels as small uppercase caps
- File list as coloured pills (green = indexed, grey = not indexed)
- Chunk count as a circular progress ring (HTML/CSS only)
- Dividers replaced by subtle borders

```python
# In the sidebar — file pills
for name in docs:
    is_indexed = vs.count() > 0
    color = "#10B981" if is_indexed else "#6B7280"
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.06); border-left:3px solid {color};
                padding:6px 10px; border-radius:4px; margin:3px 0; font-size:13px;">
        {"✓" if is_indexed else "○"}  {name}.md
    </div>
    """, unsafe_allow_html=True)
```

---

## Tier 2 — Artifact Visualisations

### 2a. Roadmap — card grid instead of markdown table

The current roadmap is a plain markdown table. Replace with a 3-column card grid:

Parse the three columns (Now / Next / Later) from the artifact content using regex, then render:

```python
def _render_roadmap(content: str):
    # parse columns...
    col1, col2, col3 = st.columns(3)
    for col, label, color, initiatives in [
        (col1, "Now", "#10B981", now_items),
        (col2, "Next", "#F59E0B", next_items),
        (col3, "Later", "#6B7280", later_items),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:{color}10; border-top:3px solid {color};
                        border-radius:0 0 10px 10px; padding:14px;">
                <div style="color:{color}; font-weight:700; font-size:13px;
                            text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">
                    {label}
                </div>
                {"".join(f'<div style="background:white; border-radius:8px; padding:10px 12px;
                          margin:6px 0; font-size:13px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                          {item}</div>' for item in initiatives)}
            </div>
            """, unsafe_allow_html=True)
```

**Parser logic:** split on `| Now |` / `| Next |` / `| Later |` table columns, strip markdown
pipe characters, collect non-separator rows.

---

### 2b. RICE Score — horizontal bar chart (Plotly)

Instead of a plain table, render a Plotly horizontal bar chart sorted by RICE score. Each bar
coloured by score bracket (green = high, amber = medium, red = low), with the four raw inputs
shown as a tooltip on hover.

```python
import plotly.graph_objects as go

def _render_rice(content: str):
    # parse markdown table → list of dicts
    rows = _parse_rice_table(content)  # returns [{initiative, reach, impact, confidence, effort, score}]

    fig = go.Figure(go.Bar(
        y=[r["initiative"] for r in rows],
        x=[r["score"] for r in rows],
        orientation="h",
        marker_color=[
            "#10B981" if r["score"] >= 200 else "#F59E0B" if r["score"] >= 80 else "#EF4444"
            for r in rows
        ],
        customdata=[[r["reach"], r["impact"], r["confidence"], r["effort"]] for r in rows],
        hovertemplate=(
            "<b>%{y}</b><br>RICE Score: %{x:.1f}<br>"
            "Reach: %{customdata[0]}  Impact: %{customdata[1]}<br>"
            "Confidence: %{customdata[2]}  Effort: %{customdata[3]} weeks"
            "<extra></extra>"
        ),
        text=[f"{r['score']:.1f}" for r in rows],
        textposition="outside",
    ))
    fig.update_layout(
        height=max(300, len(rows) * 52),
        margin=dict(l=0, r=60, t=10, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#F0EAFF", title="RICE Score"),
        yaxis=dict(autorange="reversed"),
        font=dict(family="sans-serif", size=13),
    )
    st.plotly_chart(fig, use_container_width=True)
    # Also show the raw table below the chart for reference
    st.markdown(content)
```

**Requires:** `pip install plotly` (add to `requirements.txt`)

---

### 2c. Success Metrics — styled HTML table

Replace plain markdown table with a custom HTML table that has:
- Sticky header
- Owner column rendered as coloured role badges
- Pre/Post metric cells with a green up-arrow indicator

```python
def _render_metrics(content: str):
    rows = _parse_md_table(content)  # parse rows from markdown
    rows_html = ""
    for r in rows:
        rows_html += f"""
        <tr>
          <td style="font-weight:600; padding:10px 14px;">{r['initiative']}</td>
          <td style="padding:10px 14px; color:#6B7280;">{r['pre']}</td>
          <td style="padding:10px 14px; color:#10B981; font-weight:500;">↑ {r['post']}</td>
          <td style="padding:10px 14px;">
            <span style="background:#EDE9FF; color:#5E17EB; border-radius:12px;
                         padding:3px 10px; font-size:12px; font-weight:500;">{r['owner']}</span>
          </td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%; border-collapse:collapse; font-size:14px;">
      <thead>
        <tr style="background:#5E17EB; color:white;">
          <th style="padding:10px 14px; text-align:left;">Initiative</th>
          <th style="padding:10px 14px; text-align:left;">Pre-launch</th>
          <th style="padding:10px 14px; text-align:left;">Post-launch</th>
          <th style="padding:10px 14px; text-align:left;">Owner</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)
```

---

## Tier 3 — Chat & TAO Redesign

### 3a. Role-coloured chat bubbles

User messages currently show a plain `**[Role]** message` string. Render them with a proper
role badge instead:

```python
# When rendering messages, split the [Role] prefix off and render separately
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            role_label, _, text = msg["display"].partition("] ")
            role_label = role_label.lstrip("[")
            color, icon, _ = ROLE_CONFIG.get(role_label, ("#9CA3AF", "👥", ""))
            st.markdown(f"""
            <div style="margin-bottom:6px;">
              <span style="background:{color}20; color:{color}; border-radius:12px;
                           padding:2px 10px; font-size:12px; font-weight:600;">
                {icon} {role_label}
              </span>
            </div>
            <div style="font-size:14px;">{text}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(msg["display"])
```

---

### 3b. TAO trace as collapsible pills

The current TAO trace uses `st.write()` for every step inside `st.status()`. Replace with
styled pill chips that are more compact:

```python
# Inside the stream loop — generate_response events
for i, e in enumerate(events, 1):
    type_config = {
        "search": ("🔍", "#0EA5E9", "Search"),
        "email":  ("📧", "#10B981", "Email sent"),
        "inbox":  ("📬", "#F59E0B", "Inbox read"),
        "write_staged": ("✏️", "#8B5CF6", "Change staged"),
    }
    icon, color, label = type_config.get(e["type"], ("⚡", "#5E17EB", e["type"]))
    st.markdown(f"""
    <div style="display:inline-flex; align-items:center; gap:6px;
                background:{color}15; border:1px solid {color}30;
                border-radius:20px; padding:4px 12px; margin:3px 0; font-size:12px;">
        {icon} <strong style="color:{color};">{label}</strong>
        <span style="color:#666;">— {e['detail'][:60]}</span>
    </div>
    """, unsafe_allow_html=True)
    if e.get("result_preview"):
        with st.expander("👁️ Preview", expanded=False):
            st.caption(e["result_preview"][:300])
```

---

### 3c. Pending write confirmation panel

Current panel uses `st.container(border=True)` with plain warning text. Redesign as a prominent
action card:

```python
st.markdown("""
<div style="background: linear-gradient(135deg, #FFF7ED, #FEF3C7);
            border-left: 4px solid #F59E0B; border-radius: 8px;
            padding: 16px 20px; margin: 12px 0;">
    <div style="font-weight:700; color:#92400E; font-size:14px; margin-bottom:4px;">
        ⏳ Pending File Change
    </div>
    <div style="font-size:13px; color:#78350F;">
        Review the proposed change below. Nothing is written until you confirm.
    </div>
</div>
""", unsafe_allow_html=True)
```

For delete operations — red card variant with a stronger warning.

---

## Tier 4 — Animated & Empty States

### 4a. Skeleton loader while generating artifacts

Instead of a plain spinner, show animated skeleton cards for each tab while artifacts load:

```python
# While spinner is active, show placeholder cards
skeleton_html = """
<div style="animation: pulse 1.5s ease-in-out infinite;">
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
  {cards}
</div>
""".format(cards="".join(
    f'<div style="background:#EDE9FF; border-radius:8px; height:80px; margin:8px 0;"></div>'
    for _ in range(4)
))
st.markdown(skeleton_html, unsafe_allow_html=True)
```

### 4b. Empty state when not indexed

Replace `st.info("Workflow: ...")` with a proper onboarding card showing the three steps
visually as a numbered flow:

```python
st.markdown("""
<div style="text-align:center; padding:60px 20px;">
    <div style="font-size:48px; margin-bottom:12px;">⚡</div>
    <div style="font-size:20px; font-weight:700; color:#1A0533; margin-bottom:8px;">
        Ready to generate your PM artefacts
    </div>
    <div style="color:#888; font-size:14px; margin-bottom:32px;">
        Follow these steps in the sidebar to get started
    </div>
    <div style="display:flex; justify-content:center; gap:24px; flex-wrap:wrap;">
        {steps}
    </div>
</div>
""".format(steps="".join(
    f'<div style="background:#F0EAFF; border-radius:12px; padding:16px 20px; width:160px;">'
    f'<div style="color:#5E17EB; font-size:22px;">{icon}</div>'
    f'<div style="font-weight:600; margin-top:6px; font-size:13px;">{label}</div>'
    f'</div>'
    for icon, label in [("🔍", "1. Index Documents"), ("⚡", "2. Generate Artifacts"), ("💬", "3. Start chatting")]
)), unsafe_allow_html=True)
```

### 4c. System status bar

Add a slim status strip below the hero header showing live stats:

```python
artifacts_count = len([k for k, v in st.session_state.artifacts.items() if v])
last_updated = "Not generated" if not st.session_state.artifacts else "Available"

st.markdown(f"""
<div style="display:flex; gap:24px; background:#F0EAFF; border-radius:10px;
            padding:10px 20px; margin-bottom:16px; font-size:12px; flex-wrap:wrap;">
    <span>🗄️ <strong>{vs.count()}</strong> chunks indexed</span>
    <span>📄 <strong>{len(docs)}</strong> input files</span>
    <span>📊 <strong>{artifacts_count}/6</strong> artefacts generated</span>
    <span style="color:{'#10B981' if artifacts_count == 6 else '#F59E0B'};">
        {"✓ Ready" if artifacts_count == 6 else "⚠ Index & generate to begin"}
    </span>
</div>
""", unsafe_allow_html=True)
```

---

## Implementation order

| Step | Task | Files touched | Est. time |
|------|------|--------------|-----------|
| 1 | Global CSS + hero header + role badges | `app.py` | 30 min |
| 2 | Sidebar dark theme + file pills | `app.py` | 20 min |
| 3 | Status bar | `app.py` | 10 min |
| 4 | Roadmap card grid (needs parser) | `app.py` | 45 min |
| 5 | RICE bar chart (Plotly) | `app.py`, `requirements.txt` | 40 min |
| 6 | Success Metrics HTML table | `app.py` | 30 min |
| 7 | Chat bubble role badges | `app.py` | 20 min |
| 8 | TAO pills | `app.py` | 20 min |
| 9 | Pending write card | `app.py` | 15 min |
| 10 | Empty state onboarding | `app.py` | 15 min |
| 11 | Skeleton loader | `app.py` | 20 min |

All steps are pure `app.py` changes except Step 5 (add `plotly` to `requirements.txt`).
Total: approximately 4 hours of focused implementation.

---

## What's NOT achievable in Streamlit

These would require migrating to React/Next.js (not recommended for this POC stage):
- Drag-and-drop RICE score editing
- Real-time streaming token-by-token chat output
- Animated transitions between artifact tabs
- Inline editable roadmap cards
- Persistent layout with the chat pinned to the bottom while artifacts scroll above

If the project moves toward a production release, the FastAPI server (`server.py`) already
provides all the backend endpoints needed — a React frontend would just call those.
