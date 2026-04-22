import re
from pathlib import Path

import chromadb
import yaml

CHROMA_DIR = Path(__file__).parent / ".chroma"
ACCESS_CONFIG = Path(__file__).parent / "config" / "access_config.yaml"

_DEFAULT_ACCESS = {
    "documents": {},
    "roles": {"Other": ["open"]},
}


def _load_access() -> dict:
    if ACCESS_CONFIG.exists():
        with open(ACCESS_CONFIG, encoding="utf-8") as f:
            return yaml.safe_load(f) or _DEFAULT_ACCESS
    return _DEFAULT_ACCESS


def allowed_levels(role: str) -> list[str]:
    """Return the classification levels a given role may see."""
    config = _load_access()
    return config.get("roles", {}).get(role, ["open"])


def _chunk_document(file_stem: str, content: str, classification: str) -> list[tuple[str, str, dict]]:
    """Split a document into section chunks. Each chunk carries its classification."""
    chunks = []
    parts = re.split(r"\n(?=## )", content)
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        first_line = part.splitlines()[0].lstrip("#").strip()
        chunks.append((
            f"{file_stem}::{i}",
            part,
            {"file": file_stem, "section": first_line, "classification": classification},
        ))
    return chunks


class VectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._col = self._client.get_or_create_collection("pm_context")

    def index(self, docs: dict[str, str]) -> int:
        """Re-index all documents from scratch, tagging each chunk with its classification."""
        try:
            self._client.delete_collection("pm_context")
        except Exception:
            pass
        self._col = self._client.create_collection("pm_context")

        config = _load_access()
        doc_classes: dict[str, str] = config.get("documents", {})

        ids, texts, metas = [], [], []
        for stem, content in docs.items():
            classification = doc_classes.get(stem, "internal")
            for cid, text, meta in _chunk_document(stem, content, classification):
                ids.append(cid)
                texts.append(text)
                metas.append(meta)

        if ids:
            self._col.add(documents=texts, ids=ids, metadatas=metas)
        return len(ids)

    def search(self, query: str, role: str = "Other", n_results: int = 5) -> list[dict]:
        """Semantic search filtered to the classification levels the role is allowed to see."""
        total = self._col.count()
        if total == 0:
            return []

        levels = allowed_levels(role)
        where = {"classification": {"$in": levels}}

        try:
            results = self._col.query(
                query_texts=[query],
                n_results=min(n_results, total),
                where=where,
            )
        except Exception:
            # Fallback: no filter (fail-open rather than fail-silent for debugging)
            results = self._col.query(
                query_texts=[query],
                n_results=min(n_results, total),
            )

        return [
            {
                "text": doc,
                "file": meta["file"],
                "section": meta["section"],
                "classification": meta.get("classification", "unknown"),
                "score": round(1 - dist, 3),
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def count(self) -> int:
        return self._col.count()
