# 09 — Artifact Generation & RICE Scoring

## Basics — PM artefacts

A Product Manager's core deliverables are a set of structured documents that align the team on
what to build, why, and in what order. These are not free-form essays — they follow established
formats that stakeholders across functions have learned to read quickly.

The six artefacts in this system:

| Artefact | PM purpose | Audience |
|----------|-----------|---------|
| Roadmap | Shows what's in progress, coming soon, and future | All stakeholders |
| Key Focus Areas | Explains the strategic rationale for chosen priorities | Leadership, team |
| Requirements | Defines what must be built and what's out of scope | Engineering, design |
| Success Metrics | Defines how you'll know if a feature worked | Data, leadership |
| Impact Quadrant | Visual prioritisation by impact vs. effort | PM, engineering |
| RICE Score | Quantitative prioritisation ranking | PM, leadership |

---

## Going deeper — structured output from LLMs

Generating artefacts from an LLM requires the output to be **parseable**, not just readable.
The model needs to produce six distinct sections that can be split and displayed in separate tabs.

### Delimiter-based parsing

The cleanest approach for long structured output is delimiter tokens: unique strings that mark
section boundaries. The model is instructed to include them verbatim:

```
===ROADMAP===
[roadmap content]
===KEY_FOCUS_AREAS===
[focus areas content]
...
===END===
```

Parsing is then a simple `str.find()` operation:
```python
start = raw.find("===ROADMAP===")
end = raw.find("===KEY_FOCUS_AREAS===")
roadmap_content = raw[start + len("===ROADMAP==="):end].strip()
```

Advantages over JSON output:
- Markdown tables and bullet points render naturally without escaping
- The model is less likely to hallucinate delimiter tokens than to produce malformed JSON
- Partial parsing still works if some sections are missing

### Nested delimiters for the Impact Quadrant

The quadrant needs a second level of parsing within the `===IMPACT_QUADRANT===` section:
```
--QUICK_WINS--
[bullet points]
--MAJOR_BETS--
[bullet points]
--END_QUADRANT--
```
The same `str.find()` approach works recursively.

### Retrieval queries for artefact generation

Rather than using a single broad query, 8 targeted queries retrieve diverse context:
```python
"product vision north star goals current gaps"
"roadmap priorities initiatives timeline"
"engineering capacity feasibility sprint constraints"
"customer complaints pain points feature requests tickets"
"finance budget unit economics constraints ROI"
"growth acquisition retention metrics funnels"
"competitive landscape market differentiators"
"initiative prioritisation effort reach impact confidence"
```

Results are deduplicated (exact-text match) to avoid the model seeing the same information
multiple times. The final context block is typically 20–40 unique chunks.

The queries run as `Product Manager` role — full access including restricted documents.
Artefact generation is a PM-only operation run from the sidebar, not from the chat.

---

## RICE scoring

### What RICE is

RICE is a prioritisation framework developed at Intercom. It turns the subjective "how important
is this?" question into a calculated score:

```
RICE Score = (Reach × Impact × Confidence) ÷ Effort
```

| Factor | What it measures | Scale |
|--------|----------------|-------|
| Reach | How many users/week are affected | Estimate (e.g., 500 users/week) |
| Impact | How much it moves the metric when it works | 0.25 / 0.5 / 1 / 2 / 3 |
| Confidence | How confident are you in your estimates | 10%–100% |
| Effort | Total person-weeks to design, build, and launch | Estimate |

Example:
```
Faster checkout redesign:
Reach=800, Impact=2, Confidence=80%, Effort=4 weeks
RICE = (800 × 2 × 0.80) ÷ 4 = 320
```

The RICE score has no inherent meaning by itself — its value is in comparison. An initiative
with RICE 320 should be prioritised over one with RICE 50, all else equal.

### Why RICE + Impact Quadrant together?

They serve different audiences:
- **Impact Quadrant** is *visual and qualitative* — great for a 5-minute stakeholder conversation
  where you need to show, not tell, why certain things are deprioritised
- **RICE Score** is *numerical and defensible* — great when engineering challenges a priority
  decision ("why are we building X before Y?") or when comparing across product areas

Having both means the PM has the right tool for every conversation.

---

## In this project

**Artifact queries:** `core/artifacts.py` — `_ARTIFACT_QUERIES` list, lines ~4–12. 8 queries
run as `Product Manager` role. A 9th query specific to RICE was added.

**Delimiter prompt:** `core/artifacts.py` — `_ARTIFACT_PROMPT` constant, lines ~14–57.
The RICE section instruction (lines ~44–49):
```
===RICE_SCORE===
Markdown table: Initiative | Reach (1–1000) | Impact (0.25/0.5/1/2/3) |
Confidence (10%–100%) | Effort (person-weeks) | RICE Score
RICE Score = (Reach × Impact × Confidence%) ÷ Effort. Sort descending.
Use only initiatives already in the Roadmap — do not invent new ones.
```

**Section keys and delimiters:** `core/artifacts.py` lines ~59–60.
`_SECTIONS` and `_DELIMITERS` are aligned lists — index 5 is `"rice_score"` / `"===RICE_SCORE==="`.

**Parser:** `core/artifacts.py` — `_parse_response()`, lines ~67–75. Generic — works for any
section by iterating `zip(_SECTIONS, _DELIMITERS)`. Adding a new artefact only requires adding
to the two lists, not changing the parser.

**Save + load:** `core/artifacts.py` — `save_artifacts()` writes `outputs/rice_score.md`;
`load_saved_artifacts()` reads it back on startup. Both iterate over `_SECTIONS` so they
automatically handle the new key.

**RICE tab:** `app.py` — tabs list at lines ~201–202. "RICE Score" is the 6th tab; renders
with plain `st.markdown(content)` (a markdown table renders natively in Streamlit).

**Email inclusion:** `core/email_service.py` — `_artifact_email_body()` `LABELS` dict.
`"rice_score": "RICE SCORE (Prioritisation)"` — the email loop picks it up automatically.

**Groq call for artefacts:** `core/artifacts.py` lines ~93–101. `max_tokens=4096` — artefacts
are long. No tools, no history — a single context-to-artefacts call. The system message injects
all retrieved chunks; the user message is the delimiter prompt.
