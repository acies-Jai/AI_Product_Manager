import json
import re

from groq import BadRequestError
from rag import VectorStore
from core.client import MODEL, OUTPUTS_DIR, client
from core.tools import TOOLS, run_tool


def _parse_text_tool_call(content: str) -> tuple[str, dict] | None:
    """
    Detect when the model writes a tool call as plain text instead of using the API.
    Handles patterns like:  =search_context: "query"
                            =search_context: query
    Returns (tool_name, args_dict) or None.
    """
    m = re.search(r'=(\w+):\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
    if m:
        name = m.group(1).strip()
        arg = m.group(2).strip().strip("\"'")
        if name == "search_context":
            return name, {"query": arg}
    return None

_AGENT_SYSTEM = """\
You are an expert AI Product Manager assistant at Zepto, India's leading quick commerce platform.

You have two tools:
1. search_context — queries the organisation's documents. Results are filtered to your caller's role.
   Always search before answering questions that need specific data (metrics, names, costs, feasibility).
   You may call it multiple times with different queries.
2. send_email — sends (or logs) an email. Use it when you identify a concrete action item, a decision
   that affects another team, or when the user explicitly asks you to notify someone.
   Always search for the recipient's email first if you don't have it.
3. read_file — reads a full input document. Use before proposing any update.
4. propose_update_section / propose_create_file / propose_delete_file — stage file changes for user
   confirmation. Nothing is written until the user clicks Confirm in the UI.

PM responsibilities:
- Own product vision and charter aligned to business objectives, customer problems, and system health
- Act as thought leader and decision-maker across business and tech
- Collaborate with growth/marketing, revenue, ops, data science, design, engineering, analysts
- Build and own long-term roadmaps; own feature detailing across business, design, product, and tech
- Plan and lead GTMs; own end-to-end product metrics; track pre/post-launch success
- Coach and unblock direct reports; drive cross-functional change management

When citing data, name the source file and section (e.g. "per tech.md — Feasibility Notes").
When staging a file change, clearly describe what you're proposing and that it needs confirmation."""


def run_agent(
    user_message: str,
    history: list[dict],
    vector_store: VectorStore,
    role: str = "Other",
    max_iterations: int = 8,
) -> tuple[str, list[dict], list[dict], dict | None]:
    """
    Agentic loop.

    Returns:
        reply           — final assistant text
        updated_history — full conversation for the next call
        tool_events     — [{type, detail}] for UI display
        pending_write   — first staged write operation, or None
    """
    messages = [
        {"role": "system", "content": _AGENT_SYSTEM},
        *history,
        {"role": "user", "content": user_message},
    ]
    tool_events: list[dict] = []
    pending_writes: list[dict] = []

    for _ in range(max_iterations):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=1536,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except BadRequestError as e:
            # Model generated a malformed tool call — fall back to a plain reply
            fallback = client.chat.completions.create(
                model=MODEL,
                max_tokens=1536,
                messages=messages,
            )
            reply = fallback.choices[0].message.content
            updated_history = [m for m in messages if m.get("role") != "system"]
            updated_history.append({"role": "assistant", "content": reply})
            return reply, updated_history, tool_events, None
        msg = response.choices[0].message

        if not msg.tool_calls:
            # Check if the model wrote a tool call as plain text instead of using the API
            text_call = _parse_text_tool_call(msg.content or "")
            if text_call:
                name, args = text_call
                tool_events.append({"type": "search", "detail": args.get("query", "")})
                result = run_tool(name, args, vector_store, role, pending_writes)
                # Inject results and ask for a real answer
                followup = messages + [
                    {"role": "assistant", "content": msg.content},
                    {"role": "user", "content": f"[Search results]\n{result}\n\nNow answer the original question using these results."},
                ]
                final = client.chat.completions.create(
                    model=MODEL, max_tokens=1536, messages=followup
                )
                reply = final.choices[0].message.content
                updated_history = [m for m in followup if m.get("role") != "system"]
                updated_history.append({"role": "assistant", "content": reply})
                return reply, updated_history, tool_events, pending_writes[0] if pending_writes else None

            updated_history = [m for m in messages if m.get("role") != "system"]
            updated_history.append({"role": "assistant", "content": msg.content})
            return msg.content, updated_history, tool_events, pending_writes[0] if pending_writes else None

        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            name = tc.function.name

            if name == "search_context":
                tool_events.append({"type": "search", "detail": args.get("query", "")})
            elif name == "send_email":
                tool_events.append({"type": "email", "detail": ", ".join(args.get("to", []))})
            elif name in ("propose_update_section", "propose_create_file", "propose_delete_file"):
                tool_events.append({"type": "write_staged", "detail": name})

            result = run_tool(name, args, vector_store, role, pending_writes)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "Reached iteration limit — try a more specific question.", history, tool_events, None


def log_message(role: str, user_msg: str, reply: str, tool_events: list[dict]) -> None:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    event_log = "; ".join(f"{e['type']}({e['detail']})" for e in tool_events) or "none"
    with open(OUTPUTS_DIR / "chat_log.txt", "a", encoding="utf-8") as f:
        f.write(
            f"\n{'─' * 60}\n[{role}]: {user_msg}\n"
            f"Tools: {event_log}\n[PM Assistant]: {reply}\n"
        )
