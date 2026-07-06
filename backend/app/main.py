from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agent.orchestrator import InteractiveOrchestrator
from app.schemas.api import ApprovalRequest, RunCreateRequest, RunCreateResponse
from app.storage.db import Database

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / ".interactive" / "interactive.db"
WORKSPACE = str(ROOT_DIR.parent)

app = FastAPI(title="EvoAgent Interactive Workflow Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(DB_PATH)
orchestrator = InteractiveOrchestrator(db=db, workspace=WORKSPACE)

# Hold references to in-flight run tasks so they are not garbage-collected
# mid-execution (asyncio only keeps weak references to tasks).
_BACKGROUND_TASKS: set[asyncio.Task] = set()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runs")
def list_runs(limit: int = 50, thread_id: str | None = None) -> dict:
    return {"runs": db.list_runs(limit=limit, thread_id=thread_id)}


@app.get("/stats")
def get_stats() -> dict:
    return db.stats()


@app.get("/metrics/nodes")
def metrics_nodes() -> dict:
    return {"nodes": db.node_metrics()}


@app.get("/metrics/tools")
def metrics_tools() -> dict:
    return {"tools": db.tool_metrics()}


@app.get("/metrics/timeline")
def metrics_timeline(limit: int = 20) -> dict:
    return {"timeline": db.run_timeline(limit=limit)}


@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: int) -> dict:
    art = db.get_artifact(artifact_id)
    if art is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return art


@app.post("/runs", response_model=RunCreateResponse)
async def create_run(req: RunCreateRequest) -> RunCreateResponse:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    thread_id = req.thread_id or f"thread_{uuid.uuid4().hex[:10]}"
    db.create_run(run_id, thread_id, req.mode, req.message)

    async def _worker() -> None:
        try:
            if req.mode == "mock":
                await orchestrator.run_mock(run_id, thread_id, req.message)
            else:
                await orchestrator.run_evoagent(run_id, thread_id, req.message)
        except Exception as exc:  # defensive: never let a run hang in 'running'
            db.update_run(run_id, status="failed", error=str(exc))

    task = asyncio.create_task(_worker())
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return RunCreateResponse(run_id=run_id, thread_id=thread_id, status="running")


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    row = db.get_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="run not found")
    row["artifacts"] = db.list_artifacts(run_id)
    return row


@app.get("/runs/{run_id}/artifacts")
def get_artifacts(run_id: str) -> dict:
    if db.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run_id": run_id, "artifacts": db.list_artifacts(run_id)}


@app.get("/runs/{run_id}/events/list")
def list_run_events(run_id: str, after_seq: int = 0) -> dict:
    """Non-streaming replay of a run's events ordered by seq (for replay/tests)."""
    if db.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    events = db.list_events_after(run_id, after_seq)
    return {"run_id": run_id, "events": [e.model_dump() for e in events]}


@app.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str, last_seq: int = 0) -> StreamingResponse:
    if db.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_generator():
        seq = last_seq
        while True:
            run = db.get_run(run_id)
            if run is None:
                break
            new_events = db.list_events_after(run_id, seq)
            for evt in new_events:
                seq = evt.seq
                yield f"data: {evt.model_dump_json()}\n\n"

            if run["status"] in ("completed", "failed") and not new_events:
                yield "event: end\ndata: {\"status\":\"closed\"}\n\n"
                break

            yield ": ping\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/runs/{run_id}/approve")
def approve_run(run_id: str, req: ApprovalRequest) -> dict[str, str]:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    db.update_run(run_id, approval_state="approved" if req.approved else "rejected")
    return {"run_id": run_id, "approval_state": "approved" if req.approved else "rejected"}


@app.post("/runs/{run_id}/resume")
def resume_run(run_id: str) -> dict[str, str]:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    db.update_run(run_id, status="running")
    return {"run_id": run_id, "status": "running"}


@app.get("/runs/{run_id}/memories")
def get_run_memories(run_id: str) -> dict:
    if db.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run_id": run_id, "memories": db.list_memories(run_id)}


@app.get("/memories")
def list_all_memories(limit: int = 50) -> dict:
    return {"memories": db.list_memories(None, limit)}


@app.post("/runs/{run_id}/feedback")
def submit_feedback(run_id: str, payload: dict) -> dict:
    run = db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    comment = str(payload.get("comment", "")).strip()
    score = payload.get("score")
    db.create_artifact(run_id, "feedback", "User Feedback", json.dumps({"score": score, "comment": comment}, ensure_ascii=False))
    return {"run_id": run_id, "saved": True}
