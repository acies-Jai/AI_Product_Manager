import json
import re

from rag import VectorStore
from core.client import INPUTS_DIR
from core.email_service import read_inbox, send_or_log
from core.files import read_file


def _known_emails() -> set[str]:
    """Extract all email addresses from employees.md as the authoritative allow-list."""
    path = INPUTS_DIR / "employees.md"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return {m.lower() for m in re.findall(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)}

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_context",
            "description": (
                "Semantically search the organisation's documents — product context, team constraints, "
                "metrics, budgets, tech feasibility, employee directory, and customer feedback. "
                "Call this before answering any question that requires specific organisational data. "
                "Results are automatically filtered to what the caller's role is permitted to see."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Specific question or topic"},
                    "n_results": {"type": "integer", "description": "Chunks to retrieve (1–8, default 4)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": (
                "Send an email to team members when: (1) an action item needs to be communicated, "
                "(2) the user asks to notify someone, (3) a decision affects another department. "
                "Use search_context to look up email addresses first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "array", "items": {"type": "string"}, "description": "Recipient emails"},
                    "subject": {"type": "string"},
                    "body": {"type": "string", "description": "Concise and professional"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_inbox",
            "description": (
                "Read recent emails from the Gmail inbox. Use an IMAP search string to filter "
                "by sender, subject, or date. Returns sender, subject, date, and a 500-char "
                "body snippet per email. Use when asked about stakeholder replies or incoming requests."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "IMAP search string. Examples: 'ALL', "
                            "'FROM \"boss@example.com\"', "
                            "'SUBJECT \"roadmap\" SINCE 01-Jan-2025'. "
                            "Use 'ALL' to fetch the most recent emails."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full current content of an input document. Always call before proposing an update.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File stem without .md (e.g. 'tech', 'employees')"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_update_section",
            "description": "Stage replacing a specific ## section in an input file. Nothing is written until the user confirms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "heading": {"type": "string", "description": "Exact heading text without the ## prefix"},
                    "new_content": {"type": "string", "description": "New markdown content for the section"},
                },
                "required": ["filename", "heading", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_create_file",
            "description": "Stage creating a new .md file in inputs/. Nothing is written until the user confirms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string", "description": "Full markdown content"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_delete_file",
            "description": "Stage deleting an input file. Irreversible once confirmed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                },
                "required": ["filename"],
            },
        },
    },
]

_WRITE_TOOLS = {"propose_update_section", "propose_create_file", "propose_delete_file"}


def run_tool(
    name: str,
    args: dict,
    vector_store: VectorStore,
    role: str,
    pending_writes: list,
) -> str:
    if name == "search_context":
        results = vector_store.search(args.get("query", ""), role=role, n_results=args.get("n_results", 4))
        if not results:
            return (
                "SEARCH_EMPTY: No results found for this query under the current role. "
                "This data may be classified above your access level. "
                "Do NOT answer this question from general knowledge — tell the user the information "
                "is not available for their role and suggest they ask a PM, Finance lead, or Leadership."
            )
        return "\n\n---\n\n".join(
            f"[{r['file']} / {r['section']}  |  {r['classification']}]\n{r['text']}"
            for r in results
        )

    if name == "read_inbox":
        results = read_inbox(
            query=args.get("query", "ALL"),
            max_results=args.get("max_results", 5),
        )
        if not results:
            return "No emails found matching the query. The inbox may be empty for this filter."
        if isinstance(results, list) and results and "error" in results[0]:
            return f"Inbox unavailable: {results[0]['error']}"
        return json.dumps(results, ensure_ascii=False)

    if name == "send_email":
        to: list[str] = args.get("to", [])
        if not to:
            return "No recipients provided."
        known = _known_emails()
        unknown = [addr for addr in to if addr.lower() not in known]
        if unknown:
            return (
                f"Cannot send — unknown recipient address(es): {', '.join(unknown)}. "
                "Use search_context to look up the correct email from employees.md first, "
                "then retry send_email with the verified address."
            )
        subject = args.get('subject', '')
        body = args.get('body', '')
        status = send_or_log(to, subject, body)
        return (
            f"Email {status}.\n\n"
            f"To: {', '.join(to)}\n"
            f"Subject: {subject}\n"
            f"Body:\n{body}"
        )

    if name == "read_file":
        return read_file(args["filename"])

    if name in _WRITE_TOOLS:
        pending_writes.append({"tool": name, "args": args})
        return "Change staged for user confirmation. Tell the user what you're proposing and that they must confirm before it is applied."

    return f"Unknown tool: {name}"
