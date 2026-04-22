import json

from rag import VectorStore
from core.email_service import send_or_log
from core.files import read_file

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
            return "No relevant context found (may be access-restricted for your role)."
        return "\n\n---\n\n".join(
            f"[{r['file']} / {r['section']}  |  {r['classification']}]\n{r['text']}"
            for r in results
        )

    if name == "send_email":
        to: list[str] = args.get("to", [])
        if not to:
            return "No recipients provided."
        return f"Email {send_or_log(to, args.get('subject', ''), args.get('body', ''))}."

    if name == "read_file":
        return read_file(args["filename"])

    if name in _WRITE_TOOLS:
        pending_writes.append({"tool": name, "args": args})
        return "Change staged for user confirmation. Tell the user what you're proposing and that they must confirm before it is applied."

    return f"Unknown tool: {name}"
