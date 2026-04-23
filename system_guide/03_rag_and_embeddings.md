# 03 — RAG, Embeddings & Vector Databases

## Basics — why RAG?

LLMs are trained on public data up to a cutoff date. They know nothing about your organisation's
internal documents, your team's current priorities, or last quarter's metrics. If you ask an LLM
"what is our Q3 revenue target?" without context, it either makes something up (hallucination) or
says it doesn't know.

**Retrieval-Augmented Generation (RAG)** solves this by:
1. Storing your documents in a searchable database
2. When a question arrives, searching that database for relevant excerpts
3. Injecting those excerpts into the LLM's context alongside the question
4. The LLM answers using the retrieved text as evidence

The LLM's role shifts from "recall from training" to "reason over provided text". This is much
more reliable for organisational knowledge because the source text is explicit in the context.

---

## Going deeper — embeddings

To search documents by *meaning* rather than exact keywords, we use **embeddings**.

An embedding model converts a piece of text into a vector — a list of floating-point numbers,
typically 384 to 1536 dimensions. The key property: **semantically similar texts produce vectors
that are close to each other in this high-dimensional space**.

```
"engineering sprint capacity"  →  [0.12, -0.45, 0.89, ...]
"developer bandwidth for Q3"   →  [0.14, -0.41, 0.91, ...]   ← similar vector
"quarterly revenue target"     →  [-0.72, 0.33, -0.18, ...]  ← different vector
```

Similarity is measured with **cosine similarity** (the angle between two vectors). A query is
embedded into the same vector space, and the database returns the stored chunks whose vectors are
closest to the query vector.

### Chunking strategy

Documents are split into chunks before embedding, because:
- The embedding of a 50-page document loses granularity — one vector can't represent all topics
- The LLM context window is limited — you can inject 3–5 focused chunks, not a whole document
- Answers are more precise when the injected text is tightly scoped to the question

The most common chunking boundary is natural document structure: `##` headings in markdown.
Each `## Section` becomes one chunk, along with its content until the next heading.

### Vector databases

A vector database stores chunks and their embeddings, and supports **approximate nearest-neighbour
(ANN)** search — finding the K vectors closest to a query vector efficiently (O(log n) rather
than brute-force O(n)).

Common choices:

| Database | Deployment | Best for |
|----------|-----------|---------|
| ChromaDB | Embedded (local file) | Small to medium, dev/POC |
| Pinecone | Managed cloud | Production, large scale |
| pgvector | PostgreSQL extension | When you already use Postgres |
| Weaviate | Self-hosted / cloud | Complex metadata filtering |
| Qdrant | Self-hosted / cloud | High performance + filtering |

ChromaDB (used here) runs in-process and persists data to a local directory. No separate server
needed — ideal for a POC.

### Metadata filtering

Vector similarity alone is not enough when you need access control. ChromaDB supports **metadata
filters** that restrict search results based on stored metadata fields. For example:

```python
collection.query(
    query_embeddings=[query_vec],
    where={"classification": {"$in": ["open", "internal"]}},
    n_results=3
)
```

This returns only chunks whose `classification` metadata matches the allowed set. The similarity
search still runs, but results outside the filter are excluded.

---

## In this project

**VectorStore class:** `rag.py` — entire file. Uses `chromadb.PersistentClient` pointing to
`.chroma/` in the project root.

**Embedding model:** `rag.py` — ChromaDB's default `all-MiniLM-L6-v2` via
`embedding_functions.DefaultEmbeddingFunction()`. 384-dimensional vectors.

**Chunking:** `rag.py` — `_chunk_document()` function. Splits on `\n## ` (level-2 headings).
Each chunk gets metadata: `{file, section, classification}`.

**Classification assignment:** `rag.py` — reads `config/access_config.yaml` to determine the
classification level for each file. A file not listed in the config defaults to `"open"`.

**RBAC filter:** `rag.py` — `VectorStore.search()` calls `allowed_levels(role)` to get the
permitted classification levels for the current user's role, then passes them as a ChromaDB
`where` filter. A Finance role gets `["open", "internal", "restricted"]`; a Design role gets
only `["open", "internal"]`.

**Pre-retrieval node:** `core/graph.py` — `retrieve_context` node, lines ~129–138. Runs 3
semantic searches before the agent loop for `search_query`, `file_edit`, and `email_request`
intents. Results are injected as a supplementary system message, giving the agent a head start.

**In-loop search:** `core/tools.py` — `run_tool("search_context", ...)`. The agent can call
`search_context` multiple times per turn with different queries; each call goes through
`VectorStore.search()`.

**Index trigger:** `app.py` lines ~129–136. The ↺ Index Documents button calls `vs.index(docs)`,
which re-chunks and re-embeds all current input files. Must be clicked after adding or updating
any input document.

**Persistence directory:** `.chroma/` — auto-created on first index. Contains the ChromaDB
SQLite metadata store and binary embedding files. Should not be committed to git.
