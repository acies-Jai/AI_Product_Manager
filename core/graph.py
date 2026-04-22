import json
import operator
import re
from typing import Annotated, TypedDict

from groq import BadRequestError
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from core.client import MODEL, client
from core.files import execute_write
from core.tools import TOOLS, run_tool
from rag import VectorStore


# ── State ──────────────────────────────────────────────────────────────────────

class PMState(TypedDict):
    user_message: str
    role: str
    history: Annotated[list[dict], operator.add]   # accumulates across turns via checkpointer
    retrieved_context: list[dict]                   # overwritten each turn by retrieve_context
    tool_events: list[dict]                         # overwritten each turn by generate_response
    pending_write: dict | None
    reply: str
    intent: str


# ── Shared helpers ─────────────────────────────────────────────────────────────

_INTENT_SYSTEM = """\
Classify the user message into exactly one of these labels:
- search_query    : needs data, metrics, or context from organisational documents
- file_edit       : wants to update, create, or delete an input document
- email_request   : wants to send or read emails, or notify someone
- artifact_request: wants to generate or refresh PM artefacts
- general_chat    : general PM discussion that does not need document lookup

Reply with only the label — no punctuation, no explanation."""

_AGENT_SYSTEM = """\
You are an expert AI Product Manager assistant at Zepto, India's leading quick commerce platform.

You have these tools:
1. search_context — queries the organisation's documents. Results are filtered to your caller's role.
   Always search before answering questions that need specific data (metrics, names, costs, feasibility).
   You may call it multiple times with different queries.
2. send_email — sends (or logs) an email. Use it when you identify a concrete action item, a decision
   that affects another team, or when the user explicitly asks you to notify someone.
   Always search for the recipient's email first if you don't have it.
3. read_inbox — reads recent emails from the Gmail inbox using an IMAP search string.
   Use it when asked about replies, stakeholder feedback, or incoming requests.
   Example queries: 'ALL', 'FROM "name@example.com"', 'SUBJECT "roadmap" SINCE 01-Jan-2025'.
4. read_file — reads a full input document. Use before proposing any update.
5. propose_update_section / propose_create_file / propose_delete_file — stage file changes for user
   confirmation. Nothing is written until the user clicks Confirm in the UI.

PM responsibilities:
- Own product vision and charter aligned to business objectives, customer problems, and system health
- Act as thought leader and decision-maker across business and tech
- Collaborate with growth/marketing, revenue, ops, data science, design, engineering, analysts
- Build and own long-term roadmaps; own feature detailing across business, design, product, and tech
- Plan and lead GTMs; own end-to-end product metrics; track pre/post-launch success
- Coach and unblock direct reports; drive cross-functional change management

When citing data, name the source file and section (e.g. "per tech.md — Feasibility Notes").
When staging a file change, clearly describe what you're proposing and that it needs confirmation.

STRICT RULE — never answer data questions from general knowledge:
- If search_context returns SEARCH_EMPTY, stop immediately. Do not guess, estimate, or fabricate figures.
- Tell the user clearly: "This information is restricted and not accessible for your current role."
- Suggest they contact the relevant lead (Finance, PM, or Leadership) or switch to an authorised role.
- This applies to budgets, revenue, costs, headcount, and any metric from a restricted document."""


_KNOWN_TOOLS = "search_context|read_file|read_inbox|send_email|propose_update_section|propose_create_file|propose_delete_file"

def _parse_text_tool_call(content: str) -> tuple[str, dict] | None:
    """
    Detect tool calls written as plain text instead of structured API calls.
    Handles all of:
      -search_context: "query"        (dash prefix)
      =search_context: query          (equals prefix)
      search_context: query           (bare, start of line)
    """
    m = re.search(
        rf'(?:[-=])?({_KNOWN_TOOLS}):\s*["\']?(.+?)["\']?\s*$',
        content,
        re.MULTILINE,
    )
    if not m:
        return None
    name = m.group(1).strip()
    arg = m.group(2).strip().strip("\"'")
    if name == "search_context":
        return name, {"query": arg}
    if name == "read_file":
        return name, {"filename": arg}
    if name == "read_inbox":
        return name, {"query": arg}
    return None


# ── Graph factory ──────────────────────────────────────────────────────────────

def build_graph(vector_store: VectorStore):
    """
    Factory that closes over the VectorStore instance.
    Returns a compiled LangGraph with MemorySaver checkpointer.
    Call once from app.py and store in st.session_state.graph.
    """

    # ── Nodes ──────────────────────────────────────────────────────────────────

    def classify_intent(state: PMState) -> dict:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=10,
            messages=[
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user", "content": state["user_message"]},
            ],
        )
        raw = (resp.choices[0].message.content or "general_chat").strip().lower()
        valid = {"search_query", "file_edit", "email_request", "artifact_request", "general_chat"}
        return {"intent": raw if raw in valid else "general_chat"}

    def retrieve_context(state: PMState) -> dict:
        # Skip for artifact requests and general chat — model handles those with its own tools
        if state.get("intent") in ("artifact_request", "general_chat"):
            return {"retrieved_context": []}
        results = vector_store.search(
            state["user_message"],
            role=state.get("role", "Other"),
            n_results=3,
        )
        return {"retrieved_context": results}

    def generate_response(state: PMState) -> dict:
        role = state.get("role", "Other")
        tool_events: list[dict] = []
        pending_writes: list[dict] = []

        messages: list[dict] = [{"role": "system", "content": _AGENT_SYSTEM}]

        # Inject pre-retrieved context as a supplementary system message
        ctx = state.get("retrieved_context") or []
        if ctx:
            context_text = "\n\n---\n\n".join(
                f"[{r['file']} / {r['section']}  |  {r['classification']}]\n{r['text']}"
                for r in ctx
            )
            messages.append({
                "role": "system",
                "content": f"Pre-retrieved context for this query:\n\n{context_text}",
            })

        # Conversation history from previous turns (accumulated by checkpointer)
        messages.extend(state.get("history") or [])

        # Current user message
        messages.append({"role": "user", "content": state["user_message"]})

        for _ in range(8):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    max_tokens=1536,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
            except BadRequestError:
                clean = [
                    m for m in messages
                    if m.get("role") not in ("tool",) and not m.get("tool_calls")
                ]
                fallback = client.chat.completions.create(
                    model=MODEL, max_tokens=1536, messages=clean
                )
                reply = fallback.choices[0].message.content
                return _make_return(state, reply, tool_events, pending_writes)

            msg = response.choices[0].message

            if not msg.tool_calls:
                content = msg.content or ""

                # Detect text-encoded tool calls (e.g. -search_context: "query")
                text_call = _parse_text_tool_call(content)
                if text_call:
                    name, args = text_call
                    tool_events.append({"type": "search", "detail": args.get("query", ""), "result_preview": ""})
                    result = run_tool(name, args, vector_store, role, pending_writes)
                    tool_events[-1]["result_preview"] = result[:300].strip()
                    followup = messages + [
                        {"role": "assistant", "content": content},
                        {"role": "user", "content": f"[Search results]\n{result}\n\nNow answer the original question using these results."},
                    ]
                    final = client.chat.completions.create(
                        model=MODEL, max_tokens=1536, messages=followup
                    )
                    reply = final.choices[0].message.content
                    return _make_return(state, reply, tool_events, pending_writes)

                # Detect hallucinated search narration: model describes a search but never calls the tool.
                # Force it to actually search before answering.
                _narration_patterns = (
                    "searching for", "let me search", "i'll search", "i will search",
                    "search_context", "looking up", "retrieving", "let me look",
                )
                if (
                    not tool_events  # no real tool calls yet this turn
                    and state.get("intent") in ("search_query", "email_request", "file_edit")
                    and any(p in content.lower() for p in _narration_patterns)
                ):
                    messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                    messages.append({
                        "role": "user",
                        "content": (
                            "You described a search but did not call the search_context tool. "
                            "Do NOT narrate — call search_context now with the relevant query."
                        ),
                    })
                    continue  # retry the loop so the model actually calls the tool

                return _make_return(state, content, tool_events, pending_writes)

            # Normalize assistant message to plain dict before appending
            msg_dict: dict = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(msg_dict)

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                name = tc.function.name
                # Run tool first so we can include result preview in the event
                result = run_tool(name, args, vector_store, role, pending_writes)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                preview = result[:300].strip() if isinstance(result, str) else ""
                if name == "search_context":
                    tool_events.append({"type": "search", "detail": args.get("query", ""), "result_preview": preview})
                elif name == "send_email":
                    tool_events.append({"type": "email", "detail": ", ".join(args.get("to", [])), "result_preview": result})
                elif name == "read_inbox":
                    tool_events.append({"type": "inbox", "detail": args.get("query", "ALL"), "result_preview": preview})
                elif name in ("propose_update_section", "propose_create_file", "propose_delete_file"):
                    tool_events.append({"type": "write_staged", "detail": name, "result_preview": ""})
                else:
                    tool_events.append({"type": name, "detail": str(args)[:80], "result_preview": preview})

        reply = "Reached iteration limit — try a more specific question."
        return _make_return(state, reply, tool_events, pending_writes)

    def human_confirm(state: PMState) -> dict:
        """
        Pauses graph execution via interrupt() until the user confirms or cancels.
        Resumed by app.py via graph.invoke(Command(resume=True/False), config).
        """
        confirmed = interrupt({"pending_write": state["pending_write"]})
        if confirmed:
            status = execute_write(state["pending_write"])
            return {
                "pending_write": None,
                "reply": f"Done — {status}. Use Regenerate to refresh the artifacts.",
                "history": [{"role": "assistant", "content": f"Done — {status}."}],
            }
        return {
            "pending_write": None,
            "reply": "Change cancelled — no files were modified.",
            "history": [{"role": "assistant", "content": "Change cancelled — no files were modified."}],
        }

    # ── Routing ────────────────────────────────────────────────────────────────

    def route_after_generate(state: PMState) -> str:
        return "human_confirm" if state.get("pending_write") else END

    # ── Assembly ───────────────────────────────────────────────────────────────

    builder = StateGraph(PMState)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("generate_response", generate_response)
    builder.add_node("human_confirm", human_confirm)

    builder.add_edge(START, "classify_intent")
    builder.add_edge("classify_intent", "retrieve_context")
    builder.add_edge("retrieve_context", "generate_response")
    builder.add_conditional_edges(
        "generate_response",
        route_after_generate,
        {"human_confirm": "human_confirm", END: END},
    )
    builder.add_edge("human_confirm", END)

    return builder.compile(checkpointer=MemorySaver())


_DATA_PATTERNS = re.compile(
    r"(₹\s*[\d,.]+\s*(cr|crore|lakh|l\b)|"
    r"\b\d+[\d,.]*\s*(cr|crore|%)\b|"
    r"budget|revenue|cost|headcount|allocation)",
    re.IGNORECASE,
)


def _all_searches_empty(tool_events: list[dict]) -> bool:
    """True if every search tool call returned SEARCH_EMPTY (no results for this role)."""
    searches = [e for e in tool_events if e["type"] == "search"]
    if not searches:
        return False
    return all("SEARCH_EMPTY" in e.get("result_preview", "") for e in searches)


def _should_deny_access(intent: str, tool_events: list[dict], reply: str) -> bool:
    """True when the reply likely contains hallucinated restricted data."""
    if not _DATA_PATTERNS.search(reply):
        return False
    # Case 1: searches were made but every one returned SEARCH_EMPTY
    if _all_searches_empty(tool_events):
        return True
    # Case 2: no searches at all for a data-seeking intent — model bypassed RAG entirely
    searches = [e for e in tool_events if e["type"] == "search"]
    if not searches and intent in ("search_query",):
        return True
    return False


def _make_return(
    state: PMState,
    reply: str,
    tool_events: list[dict],
    pending_writes: list[dict],
) -> dict:
    """Build the dict returned by generate_response.

    Intercepts replies that contain specific data figures when the model
    bypassed RAG or all searches returned empty — guards against hallucination
    of restricted financial/metric data.
    """
    if _should_deny_access(state.get("intent", ""), tool_events, reply):
        reply = (
            "This information is restricted and not accessible for your current role. "
            "The data you're asking about (budgets, financials, or restricted metrics) "
            "is only available to roles with the appropriate access level "
            "(Product Manager, Finance, or Leadership).\n\n"
            "Please contact the relevant lead directly or ask the PM to share a summary."
        )

    return {
        "reply": reply,
        "tool_events": tool_events,
        "pending_write": pending_writes[0] if pending_writes else None,
        "history": [
            {"role": "user", "content": state["user_message"]},
            {"role": "assistant", "content": reply},
        ],
    }
