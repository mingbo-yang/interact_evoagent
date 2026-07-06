# EvoAgent Interactive Workflow MVP

This MVP adds a web interaction system with:

1. Chat panel (frontend)
2. Real-time workflow timeline (SSE)
3. Tool-call panel
4. Artifact panel
5. FastAPI orchestrator backend
6. EvoAgent wrapper mode + mock mode

## Architecture

- **Frontend**: `frontend/` (adapted from open-source Chat UI kit `@chatscope/chat-ui-kit-react`)
- **Backend**: `backend/` (FastAPI + SQLite + SSE event stream)
- **Contract**:
  - `POST /runs`
  - `GET /runs/{run_id}`
  - `GET /runs/{run_id}/events` (SSE)
  - `POST /runs/{run_id}/approve`
  - `POST /runs/{run_id}/resume`

## Run backend

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run frontend

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"
npm run dev
```

Open http://localhost:3000

## Modes

- `mock`: deterministic mock workflow
- `evoagent`: executes real EvoAgent wrapper flow

## Code editing is native to EvoAgent (no external code agent required)

EvoAgent already ships native code tools — `write_file`, `edit_file`,
`multi_edit`, `apply_patch`, `run_tests`, `git_diff`, `bash` — so it can modify a
repository, produce a diff, and run tests **on its own**. In `evoagent` mode the
orchestrator surfaces every internal tool call EvoAgent makes as workflow events
(attributed with `source: "evoagent"`), and captures `git_diff` / `run_tests` /
`write_file` output as artifacts. So the "auto-edit code → diff → test" loop is
fully visible in the UI without Codex or Claude Code.

Verified end-to-end (real DeepSeek API): a "create a file and show git_diff"
request surfaced `write_file`, `git_diff`, `git_status`, `bash` tool events and
produced `git_diff` + `write_file` artifacts.

`CodexTool` / `ClaudeCodeTool` remain as **optional, pluggable** adapters
(`backend/app/tools/`) for delegating to an external code agent when desired;
they are not required and are stubbed by default.

## Safety and approvals

- High-risk shell actions trigger `user.approval.required`.
- Frontend has Approve / Reject controls.
- Backend emits `user.approval.received` when approved.

## API reference

- `POST /runs` — create a run (`mode`: `mock` | `evoagent`)
- `GET /runs` — list recent runs (with metrics: tool_count / event_count / duration_ms)
- `GET /runs/{run_id}` — run state + artifacts
- `GET /runs/{run_id}/events` — SSE event stream
- `GET /runs/{run_id}/events/list` — JSON replay of events (ordered by seq)
- `POST /runs/{run_id}/approve` — approve/reject a paused run
- `POST /runs/{run_id}/resume` — resume a paused run
- `GET /runs/{run_id}/artifacts` — list artifacts
- `GET /artifacts/{artifact_id}` — full artifact content (diff / test output)
- `GET /runs/{run_id}/memories` — memory records for a run
- `GET /memories` — recent memory records
- `GET /stats` — aggregate stats (runs, completed, tools, memories, avg duration)
- `POST /runs/{run_id}/feedback` — submit score/comment

## Frontend features

Polished dark design system with:

- **Run history sidebar** (collapsible) with per-run status/tool/duration and click-to-replay.
- **Live stats bar** (steps / tools / elapsed / status) updating in real time.
- **Rich workflow timeline** with node-type icons, status badges, connectors,
  duration bars, and running-node pulse animation.
- **Node detail panel** with formatted input/output/metrics (not raw JSON).
- **Tabbed bottom area**: Tool Calls, Artifacts (with colorized **diff viewer**),
  and Feedback.
- **Markdown chat** rendering, approval banner, run.failed surfacing.

## Tests

```powershell
cd backend
python -m pytest -q
```

Covers storage (seq ordering, redaction, memory roundtrip), API contract
(create/replay/approve/feedback/404s), and orchestrator routing + approval flow.
19 tests passing.

## Verified end-to-end (real DeepSeek API)

- mock run: full node chain + `memory.updated`, strictly increasing `seq`.
- evoagent run: real LLM + ShellTool (real directory listing) + artifact + memory.
- approval gate: risky command pauses with `user.approval.required`; reject emits
  `tool.failed`, approve emits `user.approval.received`.


