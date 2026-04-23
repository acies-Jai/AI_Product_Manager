import calendar
import uuid
from datetime import datetime

import streamlit as st
from langgraph.types import Command
import plotly.graph_objects as go

from core import (
    log_message,
    generate_artifacts,
    parse_quadrant_sections,
    save_artifacts,
    load_saved_artifacts,
    notify_artifacts_generated,
    load_inputs,
    execute_write,
    preview_write,
)
from core.graph import build_graph
from rag import VectorStore, allowed_levels

st.set_page_config(page_title="Zepto PM Assistant", layout="wide", page_icon="⚡")

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px; }

.stTabs [data-baseweb="tab-list"] {
    gap: 6px; background: #F0EAFF; padding: 6px; border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; padding: 6px 18px; font-weight: 500; color: #5E17EB;
}
.stTabs [aria-selected="true"] { background: #5E17EB !important; color: white !important; }

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #5E17EB, #7C3AED);
    border: none; border-radius: 8px; font-weight: 600;
    box-shadow: 0 2px 8px rgba(94,23,235,0.3);
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px); box-shadow: 0 4px 12px rgba(94,23,235,0.4);
}

[data-testid="stSidebar"] { background: #1A0533; }
[data-testid="stSidebar"] * { color: #E5D9FF !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px; color: white !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.15); }

[data-testid="stChatMessage"] { border-radius: 12px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Role config ───────────────────────────────────────────────────────────────

ROLE_CONFIG = {
    "Product Manager":          ("#5E17EB", "👤", "Full access"),
    "Finance":                  ("#10B981", "💰", "Full access"),
    "Leadership":               ("#F59E0B", "🏆", "Full access"),
    "Tech / Engineering":       ("#0EA5E9", "⚙️",  "Internal access"),
    "Design":                   ("#EC4899", "🎨", "Internal access"),
    "Growth & Marketing":       ("#F97316", "📈", "Internal access"),
    "Customer Experience (CS)": ("#14B8A6", "🎧", "Internal access"),
    "Data Science / Analytics": ("#8B5CF6", "📊", "Internal access"),
    "Operations":               ("#6B7280", "🏭", "Internal access"),
    "Other":                    ("#9CA3AF", "👥", "Public only"),
}

# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_roadmap(content: str) -> dict:
    result = {"now": [], "next": [], "later": []}
    lines = [l.strip() for l in content.strip().splitlines() if l.strip().startswith("|")]
    for i, line in enumerate(lines):
        if i == 0 or all(c in "-| :" for c in line.replace("|", "")):
            continue
        cells = [c.strip() for c in line.strip("| ").split("|")]
        if len(cells) >= 3:
            if cells[0]: result["now"].append(cells[0])
            if cells[1]: result["next"].append(cells[1])
            if cells[2]: result["later"].append(cells[2])
    return result


def _parse_rice_table(content: str) -> list:
    rows = []
    lines = [l.strip() for l in content.strip().splitlines() if l.strip().startswith("|")]
    for i, line in enumerate(lines):
        if i == 0 or all(c in "-| :" for c in line.replace("|", "")):
            continue
        cells = [c.strip() for c in line.strip("| ").split("|")]
        if len(cells) >= 6:
            try:
                score_str = cells[5].replace(",", "").strip()
                score = float(score_str) if score_str.replace(".", "").isdigit() else 0.0
                rows.append({
                    "initiative": cells[0],
                    "reach": cells[1],
                    "impact": cells[2],
                    "confidence": cells[3],
                    "effort": cells[4],
                    "score": score,
                })
            except (ValueError, IndexError):
                continue
    return sorted(rows, key=lambda r: r["score"], reverse=True)


def _parse_metrics_table(content: str) -> list:
    rows = []
    lines = [l.strip() for l in content.strip().splitlines() if l.strip().startswith("|")]
    for i, line in enumerate(lines):
        if i == 0 or all(c in "-| :" for c in line.replace("|", "")):
            continue
        cells = [c.strip() for c in line.strip("| ").split("|")]
        if len(cells) >= 4:
            rows.append({
                "initiative": cells[0],
                "pre": cells[1],
                "post": cells[2],
                "owner": cells[3],
            })
    return rows


def _parse_timeline_table(content: str) -> list:
    rows = []
    lines = [l.strip() for l in content.strip().splitlines() if l.strip().startswith("|")]
    for i, line in enumerate(lines):
        if i == 0 or all(c in "-| :" for c in line.replace("|", "")):
            continue
        cells = [c.strip() for c in line.strip("| ").split("|")]
        if len(cells) >= 4:
            try:
                start = datetime.strptime(cells[1].strip(), "%b %Y")
                end_first = datetime.strptime(cells[2].strip(), "%b %Y")
                last_day = calendar.monthrange(end_first.year, end_first.month)[1]
                end = datetime(end_first.year, end_first.month, last_day)
                rows.append({
                    "initiative": cells[0].strip(),
                    "start": start,
                    "end": end,
                    "phase": cells[3].strip(),
                })
            except ValueError:
                continue
    return rows


# ── Renderers ─────────────────────────────────────────────────────────────────

def _render_quadrant(content: str) -> None:
    sections = parse_quadrant_sections(content)
    st.markdown(
        "<div style='text-align:center;color:#888;font-size:0.82em;margin-bottom:4px'>"
        "◀ Low Effort &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        "High Effort ▶</div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(
                "<span style='font-size:1.05em;font-weight:700;color:#10B981'>🟢 Quick Wins</span>"
                "&nbsp; <span style='font-size:0.78em;color:#888'>High Impact · Low Effort</span>",
                unsafe_allow_html=True,
            )
            st.markdown(sections.get("quick_wins") or "_No items._")
    with col2:
        with st.container(border=True):
            st.markdown(
                "<span style='font-size:1.05em;font-weight:700;color:#EF4444'>🔴 Major Bets</span>"
                "&nbsp; <span style='font-size:0.78em;color:#888'>High Impact · High Effort</span>",
                unsafe_allow_html=True,
            )
            st.markdown(sections.get("major_bets") or "_No items._")
    st.markdown(
        "<div style='text-align:right;color:#888;font-size:0.82em;margin:4px 0'>▼ Low Impact</div>",
        unsafe_allow_html=True,
    )
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown(
                "<span style='font-size:1.05em;font-weight:700;color:#F59E0B'>🟡 Low-hanging Fruit</span>"
                "&nbsp; <span style='font-size:0.78em;color:#888'>Low Impact · Low Effort</span>",
                unsafe_allow_html=True,
            )
            st.markdown(sections.get("low_hanging") or "_No items._")
    with col4:
        with st.container(border=True):
            st.markdown(
                "<span style='font-size:1.05em;font-weight:700;color:#9CA3AF'>⚪ Deprioritise</span>"
                "&nbsp; <span style='font-size:0.78em;color:#888'>Low Impact · High Effort</span>",
                unsafe_allow_html=True,
            )
            st.markdown(sections.get("deprioritise") or "_No items._")


_PHASE_COLORS = {"Now": "#10B981", "Next": "#F59E0B", "Later": "#6B7280"}


def _render_gantt(timeline_content: str) -> None:
    rows = _parse_timeline_table(timeline_content)
    if not rows:
        return

    fig = go.Figure()
    for row in sorted(rows, key=lambda r: r["start"]):
        color = _PHASE_COLORS.get(row["phase"], "#5E17EB")
        duration_ms = (row["end"] - row["start"]).total_seconds() * 1000
        fig.add_trace(go.Bar(
            name=row["phase"],
            y=[row["initiative"]],
            x=[duration_ms],
            base=[row["start"].strftime("%Y-%m-%d")],
            orientation="h",
            marker_color=color,
            marker_line_width=0,
            showlegend=False,
            hovertemplate=(
                f"<b>{row['initiative']}</b><br>"
                f"{row['start'].strftime('%b %Y')} → {row['end'].strftime('%b %Y')}<br>"
                f"Phase: {row['phase']}<extra></extra>"
            ),
        ))
    fig.update_layout(
        barmode="overlay",
        height=max(280, len(rows) * 50),
        margin=dict(l=0, r=20, t=10, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(type="date", showgrid=True, gridcolor="#F0EAFF", tickformat="%b %Y"),
        yaxis=dict(autorange="reversed"),
        font=dict(family="sans-serif", size=13),
    )
    st.markdown("#### Delivery Timeline")
    legend_html = " ".join(
        f'<span style="background:{c}20; color:{c}; border:1px solid {c}40; '
        f'border-radius:12px; padding:3px 10px; font-size:12px; font-weight:600;">'
        f'{p}</span>'
        for p, c in _PHASE_COLORS.items()
    )
    st.markdown(f'<div style="margin-bottom:8px;">{legend_html}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_roadmap(content: str, timeline_content: str | None = None) -> None:
    data = _parse_roadmap(content)
    if not any(data.values()):
        st.markdown(content)
        return
    col1, col2, col3 = st.columns(3)
    for col, label, color, items in [
        (col1, "Now",   "#10B981", data["now"]),
        (col2, "Next",  "#F59E0B", data["next"]),
        (col3, "Later", "#6B7280", data["later"]),
    ]:
        with col:
            cards_html = "".join(
                f'<div style="background:white; border-radius:8px; padding:10px 12px;'
                f' margin:6px 0; font-size:13px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
                f'{item}</div>'
                for item in items
            ) if items else '<div style="color:#aaa; font-size:13px; padding:8px;">No items</div>'
            st.markdown(f"""
            <div style="background:{color}10; border-top:3px solid {color};
                        border-radius:0 0 10px 10px; padding:14px; min-height:120px;">
                <div style="color:{color}; font-weight:700; font-size:13px;
                            text-transform:uppercase; letter-spacing:1px; margin-bottom:10px;">
                    {label}
                </div>
                {cards_html}
            </div>
            """, unsafe_allow_html=True)
    if timeline_content:
        st.markdown("---")
        _render_gantt(timeline_content)


def _render_rice(content: str) -> None:
    rows = _parse_rice_table(content)
    if not rows:
        st.markdown(content)
        return
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
            "Confidence: %{customdata[2]}  Effort: %{customdata[3]}"
            "<extra></extra>"
        ),
        text=[f"{r['score']:.1f}" for r in rows],
        textposition="outside",
    ))
    fig.update_layout(
        height=max(300, len(rows) * 52),
        margin=dict(l=0, r=80, t=10, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#F0EAFF", title="RICE Score"),
        yaxis=dict(autorange="reversed"),
        font=dict(family="sans-serif", size=13),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with st.expander("View raw table", expanded=False):
        st.markdown(content)


def _render_metrics(content: str) -> None:
    rows = _parse_metrics_table(content)
    if not rows:
        st.markdown(content)
        return
    rows_html = "".join(f"""
        <tr>
          <td style="font-weight:600; padding:10px 14px; border-bottom:1px solid #F0EAFF;">{r['initiative']}</td>
          <td style="padding:10px 14px; color:#6B7280; border-bottom:1px solid #F0EAFF;">{r['pre']}</td>
          <td style="padding:10px 14px; color:#10B981; font-weight:500; border-bottom:1px solid #F0EAFF;">&#8593; {r['post']}</td>
          <td style="padding:10px 14px; border-bottom:1px solid #F0EAFF;">
            <span style="background:#EDE9FF; color:#5E17EB; border-radius:12px;
                         padding:3px 10px; font-size:12px; font-weight:500;">{r['owner']}</span>
          </td>
        </tr>""" for r in rows)
    st.markdown(f"""
    <div style="overflow-x:auto; margin-top:8px;">
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
    </div>
    """, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

if "docs" not in st.session_state:
    st.session_state.docs = load_inputs()
if "artifacts" not in st.session_state:
    st.session_state.artifacts = load_saved_artifacts()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = VectorStore()
if "pending_write" not in st.session_state:
    st.session_state.pending_write = None
if "stale_artifacts" not in st.session_state:
    st.session_state.stale_artifacts = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

docs: dict = st.session_state.docs
vs: VectorStore = st.session_state.vector_store

if "graph" not in st.session_state:
    st.session_state.graph = build_graph(vs)

graph = st.session_state.graph


def _graph_config() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread_id}}


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:12px 0 8px 0;">
        <div style="font-size:20px; font-weight:800; color:#E5D9FF; letter-spacing:-0.5px;">⚡ Zepto</div>
        <div style="font-size:11px; color:#A78BCA; text-transform:uppercase;
                    letter-spacing:2px; margin-top:2px;">PM Intelligence Layer</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:10px; text-transform:uppercase; letter-spacing:2px; color:#A78BCA;
                margin:16px 0 8px 0; font-weight:600;">Context Files</div>
    """, unsafe_allow_html=True)

    if docs:
        is_indexed = vs.count() > 0
        for name in docs:
            color = "#10B981" if is_indexed else "#6B7280"
            indicator = "✓" if is_indexed else "○"
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.06); border-left:3px solid {color};
                        padding:6px 10px; border-radius:4px; margin:3px 0;
                        font-size:13px; color:#E5D9FF;">
                {indicator}  {name}.md
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#A78BCA; font-size:13px; padding:6px 0;">No files in inputs/</div>',
            unsafe_allow_html=True,
        )

    if st.button("↺  Reload Files", use_container_width=True):
        st.session_state.docs = load_inputs()
        st.rerun()

    st.markdown('<hr style="border-color:rgba(255,255,255,0.1); margin:12px 0;">', unsafe_allow_html=True)

    chunk_count = vs.count()
    chunk_label = f"🗄️ {chunk_count} chunks indexed" if chunk_count > 0 else "🗄️ Not indexed yet"
    st.markdown(
        f'<div style="color:#A78BCA; font-size:12px; margin-bottom:8px;">{chunk_label}</div>',
        unsafe_allow_html=True,
    )

    if st.button("🔍  Index Documents", use_container_width=True):
        if not docs:
            st.error("No input files to index.")
        else:
            with st.spinner("Chunking and embedding documents…"):
                n = vs.index(docs)
            st.success(f"Indexed {n} chunks")
            st.rerun()

    st.markdown('<hr style="border-color:rgba(255,255,255,0.1); margin:12px 0;">', unsafe_allow_html=True)

    if st.button("⚡  Generate Artifacts", type="primary", use_container_width=True):
        if vs.count() == 0:
            st.error("Index documents first (🔍 Index Documents).")
        else:
            with st.spinner("Retrieving context and generating artefacts…"):
                st.session_state.artifacts = generate_artifacts(vs)
                save_artifacts(st.session_state.artifacts)
            email_status = notify_artifacts_generated(st.session_state.artifacts)
            st.success("Done — saved to outputs/")
            st.caption(f"Email: {email_status}")
            st.rerun()

    if st.session_state.artifacts:
        st.markdown(
            '<div style="color:#A78BCA; font-size:11px; margin-top:8px;">Outputs saved to outputs/</div>',
            unsafe_allow_html=True,
        )


# ── Main ─────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="background: linear-gradient(135deg, #5E17EB 0%, #7C3AED 60%, #9F67FA 100%);
            border-radius: 16px; padding: 28px 36px; margin-bottom: 20px;
            display: flex; justify-content: space-between; align-items: center;">
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
            {vs.count()} chunks indexed
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Status bar
artifacts_count = len([k for k, v in st.session_state.artifacts.items() if v])
status_color = "#10B981" if artifacts_count == 6 else "#F59E0B"
status_label = "✓ Ready" if artifacts_count == 6 else "⚠ Index &amp; generate to begin"
st.markdown(f"""
<div style="display:flex; gap:24px; background:#F0EAFF; border-radius:10px;
            padding:10px 20px; margin-bottom:16px; font-size:12px; flex-wrap:wrap; align-items:center;">
    <span>🗄️ <strong>{vs.count()}</strong> chunks indexed</span>
    <span>📄 <strong>{len(docs)}</strong> input files</span>
    <span>📊 <strong>{artifacts_count}/6</strong> artefacts generated</span>
    <span style="color:{status_color}; font-weight:600;">{status_label}</span>
</div>
""", unsafe_allow_html=True)

# Role selector
role = st.selectbox(
    "Who are you?",
    ["Product Manager", "Customer Experience (CS)", "Growth & Marketing", "Finance",
     "Tech / Engineering", "Design", "Data Science / Analytics", "Operations", "Leadership", "Other"],
    key="role",
)

_levels = allowed_levels(role)
r_color, r_icon, r_access = ROLE_CONFIG.get(role, ("#9CA3AF", "👥", "Public only"))
st.markdown(f"""
<div style="display:flex; align-items:center; gap:10px; margin-top:4px; margin-bottom:16px;">
    <span style="background:{r_color}20; color:{r_color}; border:1px solid {r_color}40;
                 border-radius:20px; padding:4px 14px; font-size:13px; font-weight:600;">
        {r_icon} {role}
    </span>
    <span style="color:#888; font-size:12px;">{r_access}</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Stale artifacts banner ────────────────────────────────────────────────────

if st.session_state.stale_artifacts and st.session_state.artifacts:
    col_warn, col_btn = st.columns([3, 1])
    with col_warn:
        st.warning("📊 Input data changed — artifacts are outdated.")
    with col_btn:
        if st.button("↻ Regenerate", use_container_width=True):
            with st.spinner("Regenerating artefacts…"):
                st.session_state.artifacts = generate_artifacts(vs)
                save_artifacts(st.session_state.artifacts)
                st.session_state.stale_artifacts = False
            st.rerun()

# ── Artifacts ─────────────────────────────────────────────────────────────────

artifacts: dict = st.session_state.artifacts

if artifacts:
    tab_labels = ["Roadmap", "Key Focus Areas", "Requirements", "Success Metrics", "Impact Quadrant", "RICE Score"]
    keys = ["roadmap", "key_focus_areas", "requirements", "success_metrics", "impact_quadrant", "rice_score"]
    tabs = st.tabs(tab_labels)
    for tab, key, label in zip(tabs, keys, tab_labels):
        with tab:
            content = artifacts.get(key)
            if not content:
                st.info(f"No content available for {label}.")
            elif key == "impact_quadrant":
                _render_quadrant(content)
            elif key == "roadmap":
                _render_roadmap(content, artifacts.get("roadmap_timeline"))
            elif key == "rice_score":
                _render_rice(content)
            elif key == "success_metrics":
                _render_metrics(content)
            else:
                st.markdown(content)
else:
    steps_html = "".join(
        f'<div style="background:#F0EAFF; border-radius:12px; padding:16px 20px;'
        f' width:160px; text-align:center;">'
        f'<div style="color:#5E17EB; font-size:22px;">{icon_}</div>'
        f'<div style="font-weight:600; margin-top:6px; font-size:13px; color:#1A0533;">{lbl}</div>'
        f'</div>'
        for icon_, lbl in [
            ("🔍", "1. Index Documents"),
            ("⚡", "2. Generate Artifacts"),
            ("💬", "3. Start chatting"),
        ]
    )
    st.markdown(f"""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-size:48px; margin-bottom:12px;">⚡</div>
        <div style="font-size:20px; font-weight:700; color:#1A0533; margin-bottom:8px;">
            Ready to generate your PM artefacts
        </div>
        <div style="color:#888; font-size:14px; margin-bottom:32px;">
            Follow these steps in the sidebar to get started
        </div>
        <div style="display:flex; justify-content:center; gap:24px; flex-wrap:wrap;">
            {steps_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Live Communication Window ─────────────────────────────────────────────────

st.subheader("Live Communication Window")
st.caption("Open to all departments. The agent searches the knowledge base before responding.")

# ── Pending write confirmation ────────────────────────────────────────────────

if st.session_state.pending_write:
    pw = st.session_state.pending_write
    is_delete = pw["tool"] == "propose_delete_file"
    if is_delete:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #FEF2F2, #FEE2E2);
                    border-left: 4px solid #EF4444; border-radius: 8px;
                    padding: 16px 20px; margin: 12px 0;">
            <div style="font-weight:700; color:#991B1B; font-size:14px; margin-bottom:4px;">
                ⚠️ Pending File Deletion
            </div>
            <div style="font-size:13px; color:#7F1D1D;">
                This action is irreversible. Review below and confirm only if you're certain.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
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
    with st.container(border=True):
        st.markdown(preview_write(pw))
        col_c, col_x = st.columns(2)
        with col_c:
            if st.button("✅ Confirm", type="primary", use_container_width=True):
                result = graph.invoke(Command(resume=True), _graph_config())
                fresh = load_inputs()
                st.session_state.docs = fresh
                vs.index(fresh)
                st.session_state.pending_write = None
                st.session_state.stale_artifacts = True
                reply = result.get("reply", "Done.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "display": reply,
                    "tool_events": [],
                })
                st.rerun()
        with col_x:
            if st.button("❌ Cancel", use_container_width=True):
                result = graph.invoke(Command(resume=False), _graph_config())
                st.session_state.pending_write = None
                reply = result.get("reply", "Change cancelled.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "display": reply,
                    "tool_events": [],
                })
                st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            display = msg.get("display", "")
            if display.startswith("**[") and "]** " in display:
                role_part, _, text = display.partition("]** ")
                role_label_hist = role_part.removeprefix("**[")
                c, ico, _ = ROLE_CONFIG.get(role_label_hist, ("#9CA3AF", "👥", ""))
                st.markdown(f"""
                <div style="margin-bottom:6px;">
                  <span style="background:{c}20; color:{c}; border-radius:12px;
                               padding:2px 10px; font-size:12px; font-weight:600;">
                    {ico} {role_label_hist}
                  </span>
                </div>
                <div style="font-size:14px;">{text}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(display)
        else:
            st.markdown(msg["display"])
            if msg.get("tool_events"):
                searches = [e for e in msg["tool_events"] if e["type"] == "search"]
                emails   = [e for e in msg["tool_events"] if e["type"] == "email"]
                inboxes  = [e for e in msg["tool_events"] if e["type"] == "inbox"]
                if searches:
                    with st.expander(f"🔍 Searched {len(searches)} time(s)", expanded=False):
                        for e in searches:
                            st.markdown(f"- `{e['detail']}`")
                for e in emails:
                    st.info(f"📧 Email sent to: {e['detail']}")
                for e in inboxes:
                    st.info(f"📬 Inbox read — query: `{e['detail']}`")

# ── Chat input ────────────────────────────────────────────────────────────────

prompt = st.chat_input("Type your message…")

if prompt:
    if vs.count() == 0:
        st.warning("Please index documents first (🔍 in the sidebar) before chatting.")
        st.stop()

    role_label: str = st.session_state.role
    user_display = f"**[{role_label}]** {prompt}"

    st.session_state.messages.append({"role": "user", "display": user_display})
    with st.chat_message("user"):
        c, ico, _ = ROLE_CONFIG.get(role_label, ("#9CA3AF", "👥", ""))
        st.markdown(f"""
        <div style="margin-bottom:6px;">
          <span style="background:{c}20; color:{c}; border-radius:12px;
                       padding:2px 10px; font-size:12px; font-weight:600;">
            {ico} {role_label}
          </span>
        </div>
        <div style="font-size:14px;">{prompt}</div>
        """, unsafe_allow_html=True)

    input_state = {
        "user_message": f"[{role_label}]: {prompt}",
        "role": role_label,
        "history": [],
        "tool_events": [],
        "pending_write": None,
    }

    with st.chat_message("assistant"):
        final_result: dict = {}

        _TAO_TYPE = {
            "search":       ("🔍", "#0EA5E9", "Search"),
            "email":        ("📧", "#10B981", "Email sent"),
            "inbox":        ("📬", "#F59E0B", "Inbox read"),
            "write_staged": ("✏️", "#8B5CF6", "Change staged"),
        }

        with st.status("🤔 Thinking…", expanded=True) as tao_status:
            for event in graph.stream(input_state, _graph_config(), stream_mode="updates"):
                for node_name, updates in event.items():
                    if node_name == "__start__":
                        continue

                    elif node_name == "classify_intent":
                        intent = updates.get("intent", "general_chat")
                        tao_status.update(label=f"💭 Intent: `{intent}`")
                        st.markdown(f"""
                        <div style="display:inline-flex; align-items:center; gap:6px;
                                    background:#0EA5E915; border:1px solid #0EA5E930;
                                    border-radius:20px; padding:4px 12px; margin:3px 0; font-size:12px;">
                            💭 <strong style="color:#0EA5E9;">Classify</strong>
                            <span style="color:#666;">— intent: {intent}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    elif node_name == "retrieve_context":
                        ctx = updates.get("retrieved_context") or []
                        if ctx:
                            sources = list(dict.fromkeys(r["file"] for r in ctx))
                            st.markdown(f"""
                            <div style="display:inline-flex; align-items:center; gap:6px;
                                        background:#8B5CF615; border:1px solid #8B5CF630;
                                        border-radius:20px; padding:4px 12px; margin:3px 0; font-size:12px;">
                                📚 <strong style="color:#8B5CF6;">Pre-fetch</strong>
                                <span style="color:#666;">— {len(ctx)} chunks from {', '.join(sources)}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                            <div style="display:inline-flex; align-items:center; gap:6px;
                                        background:#8B5CF615; border:1px solid #8B5CF630;
                                        border-radius:20px; padding:4px 12px; margin:3px 0; font-size:12px;">
                                📚 <strong style="color:#8B5CF6;">Pre-fetch</strong>
                                <span style="color:#666;">— skipped for this intent</span>
                            </div>
                            """, unsafe_allow_html=True)

                    elif node_name == "generate_response":
                        events = updates.get("tool_events") or []
                        for e in events:
                            ico_, c_, lbl_ = _TAO_TYPE.get(e["type"], ("⚡", "#5E17EB", e["type"]))
                            detail_short = e["detail"][:60]
                            st.markdown(f"""
                            <div style="display:inline-flex; align-items:center; gap:6px;
                                        background:{c_}15; border:1px solid {c_}30;
                                        border-radius:20px; padding:4px 12px; margin:3px 0; font-size:12px;">
                                {ico_} <strong style="color:{c_};">{lbl_}</strong>
                                <span style="color:#666;">— {detail_short}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            if e.get("result_preview"):
                                with st.expander("👁️ Preview", expanded=False):
                                    st.caption(e["result_preview"][:300])
                        if not events:
                            st.markdown("""
                            <div style="display:inline-flex; align-items:center; gap:6px;
                                        background:#5E17EB15; border:1px solid #5E17EB30;
                                        border-radius:20px; padding:4px 12px; margin:3px 0; font-size:12px;">
                                ⚡ <strong style="color:#5E17EB;">Direct</strong>
                                <span style="color:#666;">— no tools needed</span>
                            </div>
                            """, unsafe_allow_html=True)
                        final_result = updates

            tao_status.update(label="✅ Response ready", state="complete", expanded=False)

        reply = final_result.get("reply", "")
        tool_events = final_result.get("tool_events", [])
        pending_write = final_result.get("pending_write")

        st.markdown(reply)
        if pending_write:
            st.info("⏳ A file change has been staged — see the confirmation panel above.")

    st.session_state.pending_write = pending_write
    st.session_state.messages.append(
        {"role": "assistant", "display": reply, "tool_events": tool_events}
    )
    log_message(role_label, prompt, reply, tool_events)
    if pending_write:
        st.rerun()
