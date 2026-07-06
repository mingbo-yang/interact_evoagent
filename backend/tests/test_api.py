"""API + orchestrator integration tests.

These avoid driving the SSE endpoint through TestClient (which blocks on a
long-lived stream and does not run POST-spawned background tasks under its
per-request event loops). Instead we drive the orchestrator directly and then
assert the HTTP query/replay endpoints behave correctly.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient

from app.main import app, db, orchestrator

client = TestClient(app)


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _run_mock(message: str) -> tuple[str, str]:
    run_id = _uid("run_test")
    thread_id = _uid("thread_test")
    db.create_run(run_id, thread_id, "mock", message)
    asyncio.run(orchestrator.run_mock(run_id, thread_id, message))
    return run_id, thread_id


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_run_returns_ids():
    r = client.post("/runs", json={"message": "hello", "mode": "mock"})
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"].startswith("run_")
    assert body["thread_id"].startswith("thread_")


def test_get_unknown_run_404():
    assert client.get("/runs/does_not_exist").status_code == 404


def test_mock_run_event_sequence_and_replay():
    run_id, _ = _run_mock("请演示 workflow")

    r = client.get(f"/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r2 = client.get(f"/runs/{run_id}/events/list")
    assert r2.status_code == 200
    events = r2.json()["events"]
    types = [e["event_type"] for e in events]
    assert "run.started" in types
    assert "node.completed" in types
    assert "run.completed" in types

    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))  # strictly unique

    for e in events:
        assert e["schema_version"] == "1.0"
        assert e["source"]
        assert e["run_id"] == run_id


def test_replay_after_seq_filter():
    run_id, _ = _run_mock("trace")
    full = client.get(f"/runs/{run_id}/events/list").json()["events"]
    assert len(full) >= 3
    cut = full[1]["seq"]
    partial = client.get(f"/runs/{run_id}/events/list?after_seq={cut}").json()["events"]
    assert all(e["seq"] > cut for e in partial)


def test_memory_written_on_completion():
    run_id, _ = _run_mock("goal")
    r = client.get(f"/runs/{run_id}/memories")
    assert r.status_code == 200
    mems = r.json()["memories"]
    assert len(mems) >= 1
    assert mems[0]["user_goal"] == "goal"


def test_approve_and_feedback_endpoints():
    run_id, _ = _run_mock("x")
    ra = client.post(f"/runs/{run_id}/approve", json={"approved": True})
    assert ra.status_code == 200
    assert ra.json()["approval_state"] == "approved"

    rf = client.post(f"/runs/{run_id}/feedback", json={"score": 5, "comment": "great"})
    assert rf.status_code == 200
    assert rf.json()["saved"] is True

    arts = client.get(f"/runs/{run_id}/artifacts").json()["artifacts"]
    assert any(a["kind"] == "feedback" for a in arts)


def test_list_runs_and_stats_and_metrics():
    run_id, _ = _run_mock("stats demo")
    runs = client.get("/runs").json()["runs"]
    assert any(r["run_id"] == run_id for r in runs)
    this = next(r for r in runs if r["run_id"] == run_id)
    assert this["event_count"] >= 3  # metrics were finalized

    stats = client.get("/stats").json()
    assert stats["total_runs"] >= 1
    assert stats["completed"] >= 1
    assert "avg_duration_ms" in stats


def test_artifact_detail_endpoint():
    run_id, _ = _run_mock("artifact demo")
    client.post(f"/runs/{run_id}/feedback", json={"score": 4, "comment": "ok"})
    arts = client.get(f"/runs/{run_id}/artifacts").json()["artifacts"]
    assert arts
    aid = arts[0]["id"]
    detail = client.get(f"/artifacts/{aid}").json()
    assert detail["id"] == aid
    assert "content" in detail
    assert client.get("/artifacts/99999999").status_code == 404


def test_metrics_endpoints():
    # generate a couple of runs so aggregates are non-trivial
    _run_mock("metrics one")
    _run_mock("metrics two")

    nodes = client.get("/metrics/nodes").json()["nodes"]
    assert isinstance(nodes, list)
    assert any("node_type" in n and "avg_ms" in n for n in nodes)

    tools = client.get("/metrics/tools").json()["tools"]
    assert isinstance(tools, list)  # may be empty in pure mock, but must be a list

    timeline = client.get("/metrics/timeline?limit=10").json()["timeline"]
    assert isinstance(timeline, list)
    assert all("duration_ms" in t and "status" in t for t in timeline)


def test_resume_unknown_run_404():
    assert client.post("/runs/nope/resume").status_code == 404


def test_approval_flow_state_transitions():
    run_id = _uid("run_test")
    thread_id = _uid("thread_test")

    async def scenario():
        db.create_run(run_id, thread_id, "mock", "approve me")
        task = asyncio.create_task(orchestrator._wait_for_approval(run_id, thread_id))
        await asyncio.sleep(0.2)
        db.update_run(run_id, approval_state="approved")
        return await asyncio.wait_for(task, timeout=5)

    approved = asyncio.run(scenario())
    assert approved is True
    events = client.get(f"/runs/{run_id}/events/list").json()["events"]
    types = [e["event_type"] for e in events]
    assert "user.approval.required" in types
    assert "user.approval.received" in types
