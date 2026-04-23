"""
FastAPI server wrapping the PM Assistant graph.
Run:  uvicorn server:app --reload --port 8502
Test: curl http://localhost:8502/health
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from core import generate_artifacts, save_artifacts, notify_artifacts_generated
from core.files import load_inputs
from core.graph import build_graph
from rag import VectorStore


# ── Startup: shared state ─────────────────────────────────────────────────────

vs: VectorStore
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vs, graph
    vs = VectorStore()
    docs = load_inputs()
    if docs:
        vs.index(docs)
    graph = build_graph(vs)
    yield


app = FastAPI(title="PM Assistant API", lifespan=lifespan)


# ── Request / response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    role: str = "Product Manager"
    thread_id: str = ""          # empty → auto-generate a new session


class ChatResponse(BaseModel):
    thread_id: str
    intent: str
    reply: str
    tool_events: list[dict]
    pending_write: dict | None


class ConfirmRequest(BaseModel):
    thread_id: str
    confirmed: bool


class IndexResponse(BaseModel):
    chunks: int
    files: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "chunks_indexed": vs.count()}


@app.post("/index", response_model=IndexResponse)
def index_documents():
    docs = load_inputs()
    n = vs.index(docs)
    return {"chunks": n, "files": list(docs.keys())}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    input_state = {
        "user_message": f"[{req.role}]: {req.message}",
        "role": req.role,
        "history": [],
        "tool_events": [],
        "pending_write": None,
    }
    result: dict = {}
    for event in graph.stream(input_state, _config(thread_id), stream_mode="updates"):
        for node, updates in event.items():
            if node == "generate_response" or node == "human_confirm":
                result = updates
    if not result:
        raise HTTPException(500, "Graph produced no output")
    return ChatResponse(
        thread_id=thread_id,
        intent=result.get("intent", ""),
        reply=result.get("reply", ""),
        tool_events=result.get("tool_events") or [],
        pending_write=result.get("pending_write"),
    )


@app.post("/confirm")
def confirm(req: ConfirmRequest):
    result = graph.invoke(Command(resume=req.confirmed), _config(req.thread_id))
    return {"reply": result.get("reply", "Done.")}


@app.post("/generate-artifacts")
def gen_artifacts():
    if vs.count() == 0:
        raise HTTPException(400, "Index documents first — call POST /index")
    artifacts = generate_artifacts(vs)
    save_artifacts(artifacts)
    email_status = notify_artifacts_generated(artifacts)
    return {
        "artifacts": {k: v[:300] + "…" for k, v in artifacts.items()},
        "email_status": email_status,
    }


@app.get("/artifacts")
def get_artifacts():
    from core.artifacts import load_saved_artifacts
    return load_saved_artifacts()
