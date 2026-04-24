"""
FastAPI server wrapping the PM Assistant graph.
Run:  uvicorn server:app --reload --port 8502
Test: curl http://localhost:8502/health
"""
import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    role: str = "Product Manager"
    thread_id: str = ""


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


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "chunks_indexed": vs.count()}


@app.get("/files")
def get_files():
    docs = load_inputs()
    return {
        "files": list(docs.keys()),
        "indexed": vs.count() > 0,
        "chunks": vs.count(),
    }


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
            if node in ("generate_response", "human_confirm"):
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


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def run_graph():
        input_state = {
            "user_message": f"[{req.role}]: {req.message}",
            "role": req.role,
            "history": [],
            "tool_events": [],
            "pending_write": None,
        }
        try:
            for event in graph.stream(input_state, _config(thread_id), stream_mode="updates"):
                for node, updates in event.items():
                    if node == "__start__":
                        continue
                    payload = {
                        "node": node,
                        "updates": _sanitize(updates),
                        "thread_id": thread_id,
                    }
                    asyncio.run_coroutine_threadsafe(queue.put(payload), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    Thread(target=run_graph, daemon=True).start()

    async def event_stream():
        while True:
            item = await queue.get()
            if item is None:
                yield f"data: {json.dumps({'node': '__done__', 'thread_id': thread_id})}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/confirm")
def confirm(req: ConfirmRequest):
    result = graph.invoke(Command(resume=req.confirmed), _config(req.thread_id))
    return {"reply": result.get("reply", "Done.")}


@app.post("/generate-artifacts")
def gen_artifacts(notify: bool = False):
    if vs.count() == 0:
        raise HTTPException(400, "Index documents first — call POST /index")
    artifacts = generate_artifacts(vs)
    save_artifacts(artifacts)
    email_status = notify_artifacts_generated(artifacts) if notify else "skipped"
    return {
        "artifacts": {k: v[:300] + "…" for k, v in artifacts.items()},
        "email_status": email_status,
    }


@app.get("/team")
def get_team():
    """Return department → email mapping for the notify panel."""
    from core.email_service import _load_config
    config = _load_config()
    leads: dict = config.get("triggers", {}).get("action_item_leads", {})
    all_recipients: list = (
        config.get("triggers", {}).get("artifacts_generated", {}).get("recipients", [])
    )
    dept_labels = {
        "product": "Product",
        "tech": "Tech / Engineering",
        "cs": "Customer Support",
        "design": "Design",
        "finance": "Finance",
        "growth": "Growth & Marketing",
        "data": "Data Science",
        "operations": "Operations",
        "leadership": "Leadership",
    }
    departments = [
        {"key": dept, "label": dept_labels.get(dept, dept.title()), "emails": emails}
        for dept, emails in leads.items()
    ]
    return {"departments": departments, "all_recipients": all_recipients}


class NotifyRequest(BaseModel):
    recipients: list[str] = []  # empty = send to all configured recipients


@app.post("/notify-team")
def notify_team(req: NotifyRequest | None = None):
    from core.artifacts import load_saved_artifacts
    from core.email_service import notify_artifacts_generated, notify_with_recipients
    artifacts = load_saved_artifacts()
    if not artifacts:
        raise HTTPException(400, "No artifacts found — generate them first")
    recipients = (req.recipients if req else []) or []
    if recipients:
        email_status = notify_with_recipients(artifacts, recipients)
    else:
        email_status = notify_artifacts_generated(artifacts)
    return {"email_status": email_status}


@app.get("/artifacts")
def get_artifacts():
    from core.artifacts import load_saved_artifacts
    return load_saved_artifacts()
