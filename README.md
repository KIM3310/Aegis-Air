# Aegis-Air

> **Archived / Supporting repo**  
> The active incident-review story now lives primarily in **AegisOps** and **ops-reliability-workbench**.  
> Keep this repo as historical proof for the local-first / air-gapped incident lane.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/github/license/KIM3310/Aegis-Air)

Local-first incident review engine for teams that **cannot send production telemetry to public APIs**.

Aegis-Air probes a target service, classifies the incident locally, and returns a structured RCA with severity, failure bucket, evidence, operator questions, and immediate actions. It also ships with a replay suite so the incident taxonomy can be reviewed and regression-tested before anyone claims live-loop readiness.

## Why this repo exists

Most incident demos quietly assume cloud inference, permissive data movement, or a fake "live" dashboard. This repo is the opposite:

- **telemetry stays local**
- **structured RCA still works without the optional narrative model**
- **recorded proof stays honest when the local engine is not wired**
- **replay evidence is explicit instead of buried under UI gloss**

That makes it a better fit for restricted environments and enterprise AI reliability work.

## Aegis-Air vs AegisOps

- **Aegis-Air** is the stricter local-first / air-gapped lane: replay proof, recorded review surfaces, and no requirement to move production telemetry into public AI services.
- **AegisOps** is the broader cloud-connected operations lane: richer multimodal review, external integrations, and live cloud proof surfaces.
- If the reviewer question is **"can this incident workflow stay useful with a hard trust boundary?"**, start here.
- If the reviewer question is **"can this workflow integrate with live cloud systems and broader operator tooling?"**, start with AegisOps.

## What this repo proves

### AI engineer
- deterministic incident classification and structured RCA generation
- replay-backed regression proof instead of hand-wavy eval claims
- local-first model boundary with graceful fallback when narrative generation is unavailable

### Solutions / cloud architect
- clear separation between target API, incident-analysis engine, replay layer, and dashboard
- explicit air-gapped / recorded-review trust boundary
- deployment drafts for restricted-environment rollout discussion

### Field / solutions engineer
- crisp evaluation flow from runtime brief to replay proof to commander handoff
- copy-ready evidence surfaces for a live walkthrough
- honest demo behavior when the backend is absent

## Two-minute evaluation path

If you only have a couple of minutes, use this order:

1. **Verify the replay posture** → `python scripts/run_replay_suite.py`
2. **Open the local runtime brief** → `GET /api/runtime/brief`
3. **Open the summary pack** → `GET /api/summary-pack`
4. **Open the replay summary / full evals** → `GET /api/evals/replays/summary`, `GET /api/evals/replays`

## Honest demo boundary

- **Local engine present:** the frontend can run the live probe loop and fetch runtime / review routes from FastAPI.
- **Static Pages demo only:** the frontend falls back to recorded review data from `frontend/demo-data/`.
- **Important:** the public demo is a review surface, not a fake hosted outage-SaaS. It does not pretend to have live private telemetry when the engine is absent.

## Current proof snapshot

- **4 replay cases**
- **32 / 32 rubric checks on the bundled suite**
- **severity labels matched expected outputs across all 4 replay cases**
- **failure-bucket labels matched expected outputs across all 4 replay cases**
- **taxonomy coverage complete for the bundled replay set**

Replay buckets:

- `dependency-outage`
- `dependency-timeout`
- `latency-saturation`
- `auth-regression`

More detail: [`docs/INCIDENT_REPLAY_EVALS.md`](docs/INCIDENT_REPLAY_EVALS.md)

## Best evidence surfaces

| Surface | What it proves |
|---|---|
| `GET /health` | live-loop readiness, key links, auth posture |
| `GET /api/runtime/brief` | trust boundary, replay posture, target reachability |
| `GET /api/platform-compare` | Aegis-Air vs AegisOps lane chooser inside the engine surface |
| `GET /api/runtime/scorecard` | runtime telemetry + replay posture in one operator surface |
| `GET /api/replay-drift-board` | weakest replay areas stay visible instead of hiding behind the aggregate score |
| `GET /api/incident-command-board` | commander-facing triage of the riskiest replay cases |
| `GET /api/summary-pack` | user-friendly evidence summary and handoff contract |
| `GET /api/schema/report` | structured downstream contract for incident handoff |
| `GET /api/evals/replays` | full replay suite evidence |
| `frontend/` | operator console with recorded-review fallback |

## Architecture at a glance

### Runtime path
- `app/` — demo target API with injected checkout failures and Prometheus metrics
- `aegis_engine/` — local incident-analysis engine, replay surfaces, and frontend mount
- `frontend/` — operator console and recorded-review fallback data

### Proof path
- `tests/` — regression coverage for API, review surfaces, frontend contract, and runtime-store behavior
- `scripts/run_replay_suite.py` — replay proof runner
- `docs/` — architecture, executive summary, and discovery notes
- `infra/` — deployment drafts for discussion (`aws/` and `terraform/`)

## Repo map

```text
app/                     target API used by the local probe loop
aegis_engine/            structured RCA engine, replay/eval logic, runtime surfaces
frontend/                operator console + recorded demo payloads
tests/                   regression coverage for routes and review surface contracts
scripts/                 replay runner and runtime helpers
infra/                   restricted-environment deployment drafts
prometheus/              local metrics scrape config
docs/                    user-facing architecture and proof docs
```

## Quick Start

### Option A: quickest path with `make`

```bash
make setup
make run-target   # terminal 1
make run-engine   # terminal 2
```

Then open:

- `http://127.0.0.1:8001`

Helpful targets:

```bash
make smoke
make test
make replay
make verify
```

### Option A2: Docker compose review stack

```bash
GRAFANA_ADMIN_PASSWORD='change-me-now' docker compose up --build
```

This starts:

- target API on `http://127.0.0.1:8000`
- local engine on `http://127.0.0.1:8001`
- Prometheus on `http://127.0.0.1:9090`
- Grafana on `http://127.0.0.1:3000`

### Option B: manual commands

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Terminal 1:

```bash
uvicorn app.main:app --port 8000
```

Terminal 2:

```bash
uvicorn aegis_engine.main:app --port 8001
```

## Verification

```bash
python -m compileall -q .
python -m pytest
python scripts/run_replay_suite.py
```

Or:

```bash
make verify
```

## API surface

### Engine routes
- `GET /health`
- `GET /api/meta`
- `GET /api/platform-compare`
- `GET /api/runtime/brief`
- `GET /api/runtime/scorecard`
- `GET /api/replay-drift-board`
- `GET /api/incident-command-board`
- `GET /api/summary-pack`
- `GET /api/schema/report`
- `GET /api/chaos/trigger`
- `POST /api/incidents/report`
- `GET /api/replays`
- `GET /api/evals/replays/summary`
- `GET /api/evals/replays`
- `POST /webhook/alert`

### Target API routes
- `GET /health`
- `GET /meta`
- `GET /api/products`
- `GET /api/checkout`
- `GET /metrics`

## Example structured report

```json
{
  "status": "success",
  "report": {
    "severity": "SEV1",
    "failure_bucket": "dependency-outage",
    "summary": "checkout api is failing because a required dependency is unavailable...",
    "supporting_evidence": [
      "Observed error rate: 42.9% across 14 probes.",
      "Representative failure: Database connection lost to postgres-primary during checkout commit."
    ],
    "immediate_actions": [
      "Restore database connectivity or fail traffic over to a healthy dependency replica.",
      "Roll back recent dependency changes before widening blast radius."
    ]
  }
}
```

## Shared Evaluation Framework

Aegis-Air hosts the **single source of truth** for the cross-repo incident evaluation taxonomy, shared with AegisOps (TypeScript).

- Python schemas: `aegis_engine/shared_eval/schemas.py` (Pydantic models)
- Parameterized replay runner: `aegis_engine/shared_eval/replay_runner.py`
- Unified scoring logic: `aegis_engine/shared_eval/scoring.py`
- JSON Schema export for TypeScript consumption: `aegis_engine/shared_eval/export.py`
- Sync check: `tests/test_shared_eval_sync.py` validates that Python schemas and AegisOps TypeScript types stay compatible

To export schemas for TypeScript consumption:

```bash
python -m aegis_engine.shared_eval.export > shared-eval-schemas.json
```

To verify cross-repo compatibility:

```bash
python -m pytest tests/test_shared_eval_sync.py -v
```

## Supporting docs

- Replay eval details: [`docs/INCIDENT_REPLAY_EVALS.md`](docs/INCIDENT_REPLAY_EVALS.md)
- Architecture: [`docs/solution-architecture.md`](docs/solution-architecture.md)
- Executive one-pager: [`docs/executive-one-pager.md`](docs/executive-one-pager.md)
- Discovery notes: [`docs/discovery-guide.md`](docs/discovery-guide.md)

## Notes

- Ollama is optional. The schema-backed structured report remains the source of truth.
- `chaos_engine/chaos_mesh.py` remains a CLI driver and receives a real `rca_report` from `/webhook/alert`.
- Operator-token protection can be enabled with `AEGIS_AIR_OPERATOR_TOKEN` for mutating routes.

## Demo / links

- GitHub: https://github.com/KIM3310/Aegis-Air
- Live review surface: https://aegis-air.pages.dev

## Cloud + AI Architecture

This repository includes a neutral cloud and AI engineering blueprint that maps the current proof surface to runtime boundaries, data contracts, model-risk controls, deployment posture, and validation hooks.

- [Cloud + AI architecture blueprint](docs/cloud-ai-architecture.md)
- [Machine-readable architecture manifest](docs/architecture/blueprint.json)
- Validation command: `python3 scripts/validate_architecture_blueprint.py`
