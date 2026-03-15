# Aegis-Air Flagship Review Guide

Use this when you want the fastest honest walkthrough for a hiring manager, staff engineer, or solutions architect.

## Positioning in one sentence

Aegis-Air is a **local-first / air-gapped incident-review engine** that keeps telemetry inside the operator environment while still producing structured RCA, replay-backed proof, and handoff-ready incident surfaces.

## Best review order

### 1) Start with the trust boundary
Open:
- `GET /health`
- `GET /api/runtime/brief`

What to say:
- the repo separates recorded review from live target probing
- replay proof and live reachability are intentionally different signals
- the system does not fake live telemetry when the backend is absent

### 2) Prove the taxonomy is not hand-wavy
Open:
- `python scripts/run_replay_suite.py`
- `GET /api/evals/replays`
- `GET /api/evals/replays/summary`

What to say:
- severity and bucket classification are locked against replay cases
- the replay summary keeps weak spots visible instead of only showing an aggregate score
- the four buckets cover outage, timeout, saturation, and auth drift failure modes

### 3) Show the reviewer-first proof pack
Open:
- `GET /api/review-pack`
- `GET /api/runtime/scorecard`
- `GET /api/replay-drift-board`

What to say:
- the repo is designed for review and handoff, not only for raw API output
- the scorecard joins runtime posture with replay posture in one surface
- the drift board keeps the riskiest replay cases visible for operator attention

### 4) End on the operator console
Open:
- `/` on the engine (`http://127.0.0.1:8001` locally)

What to say:
- the frontend keeps the reviewer path above the fold
- recorded review still works when the engine is not present
- live probing is explicit and optional, not silently implied

## Proof surfaces by audience

| Audience | Best artifact | Why it matters |
|---|---|---|
| Hiring manager | `README.md` + this guide | quick story, honest scope, obvious proof path |
| AI engineer | `aegis_engine/replay_evals.py`, replay suite, tests | deterministic classification + eval grounding |
| Solutions architect | `docs/solution-architecture.md`, `/api/runtime/brief`, `infra/` | trust boundary, deployment story, restricted-env posture |
| Field / solutions engineer | `/api/review-pack`, `/api/incident-command-board`, frontend | demo flow, proof handoff, reviewer usability |

## Strong talking points

### AI engineer
- deterministic incident schema remains available even if the narrative model is down
- replay evals create a regression gate around severity and failure-bucket classification
- structured evidence, actions, and operator questions are produced from one local pipeline

### Solutions architect
- target API, engine, replay layer, and reviewer surface are separate on purpose
- recorded review is an honest mode, not a degraded fake-live mode
- operator-token support exists for mutating routes, which makes the trust boundary more credible

### Solutions / field engineer
- the repo gives you a clear show order instead of forcing improvisation
- handoff copy and proof routes are already shaped for a reviewer conversation
- the UI explains what to do first before dropping into deeper detail blocks

## Limitations to say out loud

These are strengths when stated honestly:

- this is not a hosted multi-tenant incident platform
- the public Pages surface is a recorded-review pack, not a live backend demo
- deployment drafts exist, but production hardening is intentionally not oversold
- Ollama narrative generation is optional; the schema-backed report is the real contract

## Suggested live demo flow

1. `make setup`
2. `make run-target`
3. `make run-engine`
4. open `http://127.0.0.1:8001`
5. walk runtime brief → replay suite → review pack → optional live probe loop

## Files worth reading after the demo

- `README.md`
- `docs/solution-architecture.md`
- `docs/executive-one-pager.md`
- `docs/INCIDENT_REPLAY_EVALS.md`
- `tests/test_meta_endpoints.py`
- `tests/test_runtime_store.py`
