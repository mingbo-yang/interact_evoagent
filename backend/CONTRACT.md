# Interactive Workflow Contract (MVP v1)

## Transport

- Streaming: **SSE only**
- Content type: `text/event-stream`

## API

1. `POST /runs` create run
2. `GET /runs/{run_id}` query run state
3. `GET /runs/{run_id}/events` stream workflow events
4. `POST /runs/{run_id}/approve` send approval decision
5. `POST /runs/{run_id}/resume` resume paused run
6. `GET /runs/{run_id}/artifacts` fetch generated artifacts
7. `POST /runs/{run_id}/feedback` submit user feedback

## Event ordering

- Events are ordered by `run_id + seq`
- `seq` is strictly increasing per run
- Frontend deduplicates/reorders by `(run_id, seq)`

## Required event fields

- `schema_version`
- `event_id`
- `event_type`
- `source`
- `run_id`
- `thread_id`
- `seq`
- `status` (when applicable)
- `error` (for failed events)

