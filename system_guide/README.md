# System Guide — Index

Reference documentation for the Zepto PM Assistant. Each file covers a concept from basics
through deep mechanics, then closes with exactly where the concept is implemented in this codebase.

| File | Topic | Key concepts |
|------|-------|-------------|
| [00_overview.md](00_overview.md) | Project overview & architecture | 5-layer diagram, full data flow, file map, glossary |
| [01_agentic_ai.md](01_agentic_ai.md) | Agentic AI & the ReAct pattern | Tool calling, TAO cycle, iteration limits, text tool call fallback |
| [02_llm_and_tool_calling.md](02_llm_and_tool_calling.md) | LLMs, prompting & Groq API | Messages format, system prompts, token limits, BadRequestError |
| [03_rag_and_embeddings.md](03_rag_and_embeddings.md) | RAG, embeddings & ChromaDB | Semantic search, vector databases, chunking, metadata filtering |
| [04_rbac.md](04_rbac.md) | Role-based access control | Classification levels, honour-system vs. enforced, SEARCH_EMPTY |
| [05_langgraph.md](05_langgraph.md) | LangGraph state machines | StateGraph, reducers, checkpointers, interrupt/resume, streaming |
| [06_hallucination_guards.md](06_hallucination_guards.md) | Hallucination & defence in depth | 3-layer guard, narration detection, post-reply intercept |
| [07_document_update_flow.md](07_document_update_flow.md) | Document update & HITL | Propose/confirm pattern, regex section replace, stale artifacts |
| [08_email_integration.md](08_email_integration.md) | SMTP + IMAP email | Gmail App Passwords, send/receive, allow-list guard |
| [09_artifacts_and_rice.md](09_artifacts_and_rice.md) | Artifact generation & RICE scoring | Delimiter parsing, retrieval queries, RICE formula, Impact Quadrant |
| [10_faq.md](10_faq.md) | Frequently asked questions | 20 Q&A pairs covering architecture, RAG, agents, email, operations |

## Recommended reading order

**New to agentic AI entirely:** 01 → 02 → 03 → 05 → 00

**Know ML/NLP, new to agents:** 01 → 05 → 06 → 07 → 00

**Engineer onboarding to this project:** 00 → 04 → 07 → 09 → 10

**Demo prep / Q&A readiness:** 00 → 10 → skim relevant concept files
