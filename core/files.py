import re

from core.client import INPUTS_DIR


def load_inputs() -> dict[str, str]:
    docs: dict[str, str] = {}
    if INPUTS_DIR.exists():
        for f in sorted(INPUTS_DIR.glob("*.md")):
            docs[f.stem] = f.read_text(encoding="utf-8")
    return docs


def read_file(filename: str) -> str:
    path = INPUTS_DIR / f"{filename}.md"
    if not path.exists():
        return f"File '{filename}.md' not found in inputs/."
    return path.read_text(encoding="utf-8")


# ── Write execution (called from app.py after user confirms) ──────────────────

def execute_write(operation: dict) -> str:
    tool = operation["tool"]
    args = operation["args"]
    if tool == "propose_update_section":
        return _exec_update_section(args["filename"], args["heading"], args["new_content"])
    if tool == "propose_create_file":
        return _exec_create_file(args["filename"], args["content"])
    if tool == "propose_delete_file":
        return _exec_delete_file(args["filename"])
    return f"Unknown operation: {tool}"


def preview_write(operation: dict) -> str:
    """Human-readable diff shown in the confirmation panel."""
    tool = operation["tool"]
    args = operation["args"]
    if tool == "propose_update_section":
        current = ""
        path = INPUTS_DIR / f"{args['filename']}.md"
        clean_heading = args['heading'].lstrip("#").strip()
        if path.exists():
            match = re.search(
                rf"## {re.escape(clean_heading)}\s*\n(.*?)(?=\n## |\Z)",
                path.read_text(encoding="utf-8"),
                re.DOTALL | re.IGNORECASE,
            )
            current = match.group(1).strip() if match else "(section not found)"
        return (
            f"**File:** `inputs/{args['filename']}.md`\n"
            f"**Section:** `## {clean_heading}`\n\n"
            f"**Current:**\n{current}\n\n"
            f"**Proposed:**\n{args['new_content']}"
        )
    if tool == "propose_create_file":
        return f"**Create:** `inputs/{args['filename']}.md`\n\n{args['content']}"
    if tool == "propose_delete_file":
        return f"**Delete:** `inputs/{args['filename']}.md`"
    return str(operation)


def _exec_update_section(filename: str, heading: str, new_content: str) -> str:
    path = INPUTS_DIR / f"{filename}.md"
    if not path.exists():
        # Try without .md suffix in case model included it
        alt = INPUTS_DIR / filename
        if alt.exists():
            path = alt
        else:
            return f"File '{filename}.md' not found in inputs/."
    content = path.read_text(encoding="utf-8")
    # Strip any leading `#` characters and whitespace the model may have included
    clean_heading = heading.lstrip("#").strip()
    pattern = rf"(## {re.escape(clean_heading)}\s*\n).*?(?=\n## |\Z)"
    if not re.search(pattern, content, re.DOTALL | re.IGNORECASE):
        return (
            f"Section '## {clean_heading}' not found in {filename}.md — no changes made. "
            f"Available sections: {', '.join(re.findall(r'^## (.+)', content, re.MULTILINE))}"
        )
    updated = re.sub(pattern, rf"\g<1>{new_content.strip()}", content, flags=re.DOTALL | re.IGNORECASE)
    path.write_text(updated, encoding="utf-8")
    return f"Updated '## {clean_heading}' in {filename}.md"


def _exec_create_file(filename: str, content: str) -> str:
    path = INPUTS_DIR / f"{filename}.md"
    if path.exists():
        return f"'{filename}.md' already exists — use propose_update_section to modify it."
    path.write_text(content, encoding="utf-8")
    return f"Created inputs/{filename}.md"


def _exec_delete_file(filename: str) -> str:
    path = INPUTS_DIR / f"{filename}.md"
    if not path.exists():
        return f"File '{filename}.md' not found."
    path.unlink()
    return f"Deleted inputs/{filename}.md"
