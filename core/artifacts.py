from rag import VectorStore
from core.client import MODEL, OUTPUTS_DIR, client

_ARTIFACT_QUERIES = [
    "product vision north star goals current gaps",
    "roadmap priorities initiatives timeline",
    "engineering capacity feasibility sprint constraints",
    "customer complaints pain points feature requests tickets",
    "finance budget unit economics constraints ROI",
    "growth acquisition retention metrics funnels",
    "competitive landscape market differentiators",
]

_ARTIFACT_PROMPT = """\
Generate a complete set of PM artefacts for the current product phase based on the context provided.

Use EXACTLY this delimiter format — include each ===SECTION=== line verbatim:

===ROADMAP===
Markdown table with columns Now / Next / Later. Each cell has 2-4 initiatives with one-line descriptions.

===KEY_FOCUS_AREAS===
4-5 numbered focus areas. Each has a bold title and one-paragraph rationale grounded in the org context.

===REQUIREMENTS===
Three labelled sections — Requirements (what stakeholders need), Scope (in/out), Final Specification (acceptance criteria per requirement).

===SUCCESS_METRICS===
Markdown table with columns: Initiative | Pre-launch Metric | Post-launch Metric | Owner.

===IMPACT_QUADRANT===
Use EXACTLY these sub-delimiters within this section. Each section should have 3-5 bullet points:
--QUICK_WINS--
[bullet points — High Impact, Low Effort initiatives]
--MAJOR_BETS--
[bullet points — High Impact, High Effort initiatives]
--LOW_HANGING--
[bullet points — Low Impact, Low Effort initiatives]
--DEPRIORITISE--
[bullet points — Low Impact, High Effort initiatives]
--END_QUADRANT--

===END===

Replace the description under each delimiter with the actual content. No extra text outside the delimiters."""

_SECTIONS = ["roadmap", "key_focus_areas", "requirements", "success_metrics", "impact_quadrant"]
_DELIMITERS = ["===ROADMAP===", "===KEY_FOCUS_AREAS===", "===REQUIREMENTS===",
               "===SUCCESS_METRICS===", "===IMPACT_QUADRANT===", "===END==="]

_QUAD_KEYS = ["quick_wins", "major_bets", "low_hanging", "deprioritise"]
_QUAD_DELIMS = ["--QUICK_WINS--", "--MAJOR_BETS--", "--LOW_HANGING--", "--DEPRIORITISE--", "--END_QUADRANT--"]


def _parse_response(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for i, (key, delim) in enumerate(zip(_SECTIONS, _DELIMITERS)):
        start = raw.find(delim)
        end = raw.find(_DELIMITERS[i + 1])
        if start != -1 and end != -1:
            result[key] = raw[start + len(delim):end].strip()
    if not result:
        result["roadmap"] = f"Could not parse response. Raw output:\n\n{raw}"
    return result


def parse_quadrant_sections(content: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for i, (key, delim) in enumerate(zip(_QUAD_KEYS, _QUAD_DELIMS)):
        start = content.find(delim)
        end = content.find(_QUAD_DELIMS[i + 1])
        if start != -1 and end != -1:
            result[key] = content[start + len(delim):end].strip()
        elif start != -1:
            result[key] = content[start + len(delim):].strip()
    return result


def generate_artifacts(vector_store: VectorStore) -> dict[str, str]:
    seen: set[str] = set()
    context_parts: list[str] = []
    for q in _ARTIFACT_QUERIES:
        for chunk in vector_store.search(q, role="Product Manager", n_results=4):
            if chunk["text"] not in seen:
                seen.add(chunk["text"])
                context_parts.append(f"[{chunk['file']} / {chunk['section']}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)
    system = (
        "You are a PM assistant at Zepto. Below is relevant organisational context retrieved for you.\n\n"
        "=== RETRIEVED CONTEXT ===\n" + context + "\n=== END CONTEXT ==="
    )
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _ARTIFACT_PROMPT},
        ],
    )
    return _parse_response(response.choices[0].message.content.strip())


def save_artifacts(artifacts: dict[str, str]) -> None:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    for key, content in artifacts.items():
        (OUTPUTS_DIR / f"{key}.md").write_text(content, encoding="utf-8")
