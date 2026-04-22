import streamlit as st

from core import (
    run_agent,
    log_message,
    generate_artifacts,
    parse_quadrant_sections,
    save_artifacts,
    notify_artifacts_generated,
    load_inputs,
    execute_write,
    preview_write,
)
from rag import VectorStore, allowed_levels

st.set_page_config(page_title="Zepto PM Assistant", layout="wide", page_icon="⚡")


# ── Quadrant renderer ─────────────────────────────────────────────────────────

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


# ── Session state ─────────────────────────────────────────────────────────────

if "docs" not in st.session_state:
    st.session_state.docs = load_inputs()
if "artifacts" not in st.session_state:
    st.session_state.artifacts = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_history" not in st.session_state:
    st.session_state.agent_history = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = VectorStore()
if "pending_write" not in st.session_state:
    st.session_state.pending_write = None
if "stale_artifacts" not in st.session_state:
    st.session_state.stale_artifacts = False

docs: dict = st.session_state.docs
vs: VectorStore = st.session_state.vector_store


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h2 style='color:#5E17EB;margin-bottom:0'>⚡ Zepto</h2>"
        "<p style='color:#888;margin-top:2px;font-size:0.85em'>PM Intelligence Layer</p>",
        unsafe_allow_html=True,
    )

    st.subheader("Context Files")
    if docs:
        for name in docs:
            st.success(f"✓  {name}.md")
    else:
        st.warning("No files found in inputs/")

    if st.button("↺  Reload Files", use_container_width=True):
        st.session_state.docs = load_inputs()
        st.rerun()

    st.divider()

    chunk_count = vs.count()
    st.caption(f"Vector store: {chunk_count} chunks indexed" if chunk_count > 0 else "Vector store: not indexed yet")

    if st.button("🔍  Index Documents", use_container_width=True):
        if not docs:
            st.error("No input files to index.")
        else:
            with st.spinner("Chunking and embedding documents…"):
                n = vs.index(docs)
            st.success(f"Indexed {n} chunks")
            st.rerun()

    st.divider()

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

    if st.session_state.artifacts:
        st.caption("Outputs saved to outputs/")


# ── Main ─────────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='margin-bottom:0'>Product Manager Assistant</h1>"
    "<p style='color:#888;margin-top:4px'>Charter: Customer App & Checkout Experience</p>",
    unsafe_allow_html=True,
)

role = st.selectbox(
    "Who are you?",
    ["Product Manager", "Customer Experience (CS)", "Growth & Marketing", "Finance",
     "Tech / Engineering", "Design", "Data Science / Analytics", "Operations", "Leadership", "Other"],
    key="role",
)

_levels = allowed_levels(role)
if "restricted" in _levels:
    st.caption("🔓 Access: Full — including restricted data (Finance, Leadership, PM only)")
elif "internal" in _levels:
    st.caption("🔒 Access: Internal — finance data is restricted for your role")
else:
    st.caption("🔒 Access: Public only")

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
    tabs = st.tabs(["Roadmap", "Key Focus Areas", "Requirements", "Success Metrics", "Impact Quadrant"])
    keys = ["roadmap", "key_focus_areas", "requirements", "success_metrics", "impact_quadrant"]
    for tab, key, label in zip(tabs, keys, ["Roadmap", "Key Focus Areas", "Requirements", "Success Metrics", "Impact Quadrant"]):
        with tab:
            content = artifacts.get(key)
            if not content:
                st.info(f"No content available for {label}.")
            elif key == "impact_quadrant":
                _render_quadrant(content)
            else:
                st.markdown(content)
else:
    st.info("**Workflow:** 🔍 Index Documents → ⚡ Generate Artifacts (both in the sidebar)")

st.divider()

# ── Live Communication Window ─────────────────────────────────────────────────

st.subheader("Live Communication Window")
st.caption("Open to all departments. The agent searches the knowledge base before responding.")

# Pending write confirmation
if st.session_state.pending_write:
    pw = st.session_state.pending_write
    is_delete = pw["tool"] == "propose_delete_file"
    with st.container(border=True):
        if is_delete:
            st.error("⚠️ Pending change — confirm to apply (irreversible)")
        else:
            st.warning("⏳ Pending change — confirm to apply")
        st.markdown(preview_write(pw))
        col_c, col_x = st.columns(2)
        with col_c:
            if st.button("✅ Confirm", type="primary", use_container_width=True):
                status = execute_write(pw)
                fresh = load_inputs()
                st.session_state.docs = fresh
                vs.index(fresh)
                st.session_state.pending_write = None
                st.session_state.stale_artifacts = True
                st.session_state.messages.append({
                    "role": "assistant",
                    "display": f"✅ Done — {status}. Use **↻ Regenerate** to refresh the artifacts.",
                    "tool_events": [],
                })
                st.rerun()
        with col_x:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.pending_write = None
                st.session_state.messages.append({
                    "role": "assistant",
                    "display": "Change cancelled — no files were modified.",
                    "tool_events": [],
                })
                st.rerun()

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display"])
        if msg["role"] == "assistant" and msg.get("tool_events"):
            searches = [e for e in msg["tool_events"] if e["type"] == "search"]
            emails = [e for e in msg["tool_events"] if e["type"] == "email"]
            if searches:
                with st.expander(f"🔍 Searched {len(searches)} time(s)", expanded=False):
                    for e in searches:
                        st.markdown(f"- `{e['detail']}`")
            for e in emails:
                st.info(f"📧 Email sent to: {e['detail']}")

# Chat input
prompt = st.chat_input("Type your message…")

if prompt:
    if vs.count() == 0:
        st.warning("Please index documents first (🔍 in the sidebar) before chatting.")
        st.stop()

    role_label: str = st.session_state.role
    user_display = f"**[{role_label}]** {prompt}"

    st.session_state.messages.append({"role": "user", "display": user_display})
    with st.chat_message("user"):
        st.markdown(user_display)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base…"):
            reply, updated_history, tool_events, pending_write = run_agent(
                f"[{role_label}]: {prompt}",
                st.session_state.agent_history,
                vs,
                role=role_label,
            )
        st.markdown(reply)
        searches = [e for e in tool_events if e["type"] == "search"]
        emails = [e for e in tool_events if e["type"] == "email"]
        if searches:
            with st.expander(f"🔍 Searched {len(searches)} time(s)", expanded=False):
                for e in searches:
                    st.markdown(f"- `{e['detail']}`")
        for e in emails:
            st.info(f"📧 Email sent to: {e['detail']}")
        if pending_write:
            st.info("⏳ A file change has been staged — see the confirmation panel above.")

    st.session_state.agent_history = updated_history
    st.session_state.pending_write = pending_write
    st.session_state.messages.append(
        {"role": "assistant", "display": reply, "tool_events": tool_events}
    )
    log_message(role_label, prompt, reply, tool_events)
    if pending_write:
        st.rerun()
