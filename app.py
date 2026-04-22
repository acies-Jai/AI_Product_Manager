import uuid

import streamlit as st
from langgraph.types import Command

from core import (
    log_message,
    generate_artifacts,
    parse_quadrant_sections,
    save_artifacts,
    notify_artifacts_generated,
    load_inputs,
    execute_write,
    preview_write,
)
from core.graph import build_graph
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

# Build graph once per session — closes over the VectorStore instance
if "graph" not in st.session_state:
    st.session_state.graph = build_graph(vs)

graph = st.session_state.graph


def _graph_config() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread_id}}


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

# ── Pending write confirmation ────────────────────────────────────────────────

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
        st.markdown(msg["display"])
        if msg["role"] == "assistant" and msg.get("tool_events"):
            searches = [e for e in msg["tool_events"] if e["type"] == "search"]
            emails = [e for e in msg["tool_events"] if e["type"] == "email"]
            inboxes = [e for e in msg["tool_events"] if e["type"] == "inbox"]
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
        st.markdown(user_display)

    # Input state — only pass fields that change each turn.
    # history uses operator.add reducer so passing [] is a no-op accumulation.
    input_state = {
        "user_message": f"[{role_label}]: {prompt}",
        "role": role_label,
        "history": [],
        "tool_events": [],
        "pending_write": None,
    }

    with st.chat_message("assistant"):
        final_result: dict = {}

        with st.status("🤔 Thinking…", expanded=True) as tao_status:
            for event in graph.stream(input_state, _graph_config(), stream_mode="updates"):
                for node_name, updates in event.items():
                    if node_name == "__start__":
                        continue

                    elif node_name == "classify_intent":
                        intent = updates.get("intent", "general_chat")
                        tao_status.update(label=f"💭 Intent: `{intent}`")
                        st.write(f"**💭 Think** — classified intent as `{intent}`")

                    elif node_name == "retrieve_context":
                        ctx = updates.get("retrieved_context") or []
                        if ctx:
                            sources = list(dict.fromkeys(r["file"] for r in ctx))
                            st.write(f"**📚 Pre-fetch** — {len(ctx)} chunks from `{'`, `'.join(sources)}`")
                        else:
                            st.write("**📚 Pre-fetch** — skipped for this intent")

                    elif node_name == "generate_response":
                        events = updates.get("tool_events") or []
                        for i, e in enumerate(events, 1):
                            if e["type"] == "search":
                                st.write(f"**⚡ Act [{i}]** — `search_context`: \"{e['detail']}\"")
                                if e.get("result_preview"):
                                    st.caption(f"👁️ Observe: {e['result_preview'][:200]}")
                            elif e["type"] == "email":
                                st.write(f"**⚡ Act [{i}]** — `send_email` → {e['detail']}")
                                st.caption(f"👁️ Observe: {e.get('result_preview', 'sent')}")
                            elif e["type"] == "inbox":
                                st.write(f"**⚡ Act [{i}]** — `read_inbox`: \"{e['detail']}\"")
                                if e.get("result_preview"):
                                    st.caption(f"👁️ Observe: {e['result_preview'][:200]}")
                            elif e["type"] == "write_staged":
                                st.write(f"**⚡ Act [{i}]** — `{e['detail']}` staged for confirmation")
                        if not events:
                            st.write("**⚡ Act** — direct response (no tools needed)")
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
