# Aegis-Air

Local-first incident review engine for teams that **cannot send production telemetry to public APIs**.

Aegis-Air probes a target service, classifies the incident locally, and returns a structured RCA with severity, failure bucket, evidence, operator questions, and immediate actions. It also ships with a replay suite so the incident taxonomy can be reviewed and regression-tested before anyone claims live-loop readiness.

## Portfolio posture

- Read this repo like the restricted-environment counterpart to `AegisOps`, not like a generic incident dashboard.
- The core proof is local-first incident classification plus replay-backed confidence, not UI gloss.
- In the broader portfolio, this is the repo that makes the public reliability story believable for teams with hard data-boundary constraints.

## Best target-team fit

| Team lens | What should stand out fast | Start here |
|---|---|---|
| Frontier / runtime reliability | local-first trust boundary, structured RCA contract, replay proof | [`docs/FLAGSHIP_REVIEW_GUIDE.md`](docs/FLAGSHIP_REVIEW_GUIDE.md), `GET /api/runtime/brief`, `GET /api/review-pack` |
| Big tech / SRE / infra | deterministic incident classification, explicit fallback posture, honest demo boundary | `GET /health`, `GET /api/runtime/scorecard`, `python scripts/run_replay_suite.py` |
| High-trust workflow systems | operator-ready handoff artifacts, evidence-first RCA, reviewable restricted-environment workflow | `GET /api/incident-command-board`, `GET /api/schema/report`, `GET /api/evals/replays` |

## Portfolio context

- **Portfolio family:** incident AI, runtime safety, restricted-environment systems
- **This repo's role:** local-first proof that the reliability story still holds when public model APIs are off the table
- **Related repos:** `stage-pilot`, `AegisOps`, `twincity-ui`

## Big-Tech Elevation Track

- Canonical execution plan: [`docs/BIGTECH_ELEVATION_PLAN.md`](docs/BIGTECH_ELEVATION_PLAN.md)
- Goal: turn this repo into the canonical air-gapped incident runtime counterpart to `AegisOps`.

## Why this repo exists

Most incident demos quietly assume cloud inference, permissive data movement, or a fake "live" dashboard. This repo is the opposite:

- **telemetry stays local**
- **structured RCA still works without the optional narrative model**
- **recorded proof stays honest when the local engine is not wired**
- **replay evidence is explicit instead of buried under UI gloss**

That makes it a stronger portfolio artifact for restricted environments, enterprise AI reliability work, and solutions architecture conversations.

## What this repo proves

### AI engineer
- deterministic incident classification and structured RCA generation
- replay-backed regression proof instead of hand-wavy eval claims
- local-first model boundary with graceful fallback when narrative generation is unavailable

### Solutions / cloud architect
- clear separation between target API, incident-analysis engine, replay layer, and reviewer surface
- explicit air-gapped / recorded-review trust boundary
- deployment drafts for restricted-environment rollout discussion

### Field / solutions engineer
- crisp reviewer flow from runtime brief to replay proof to commander handoff
- copy-ready proof surfaces for a live walkthrough
- honest demo behavior when the backend is absent

## Two-minute reviewer path

If you only have a couple of minutes, use this order:

1. **Read the flagship walkthrough** → [`docs/FLAGSHIP_REVIEW_GUIDE.md`](docs/FLAGSHIP_REVIEW_GUIDE.md)
2. **Verify the replay posture** → `python scripts/run_replay_suite.py`
3. **Open the local runtime brief** → `GET /api/runtime/brief`
4. **Open the reviewer pack** → `GET /api/review-pack`
5. **Open the replay summary / full evals** → `GET /api/evals/replays/summary`, `GET /api/evals/replays`

## Honest demo boundary

- **Local engine present:** the frontend can run the live probe loop and fetch runtime / review routes from FastAPI.
- **Static Pages demo only:** the frontend falls back to recorded review data from `frontend/demo-data/`.
- **Important:** the public demo is a review surface, not a fake hosted outage-SaaS. It does not pretend to have live private telemetry when the engine is absent.

## Current proof snapshot

- **4 replay cases**
- **32 / 32 rubric checks**
- **100% severity accuracy**
- **100% failure-bucket accuracy**
- **100% taxonomy coverage**

Replay buckets:

- `dependency-outage`
- `dependency-timeout`
- `latency-saturation`
- `auth-regression`

More detail: [`docs/INCIDENT_REPLAY_EVALS.md`](docs/INCIDENT_REPLAY_EVALS.md)

## Best proof surfaces

| Surface | What it proves |
|---|---|
| `GET /health` | live-loop readiness, key links, auth posture |
| `GET /api/runtime/brief` | trust boundary, replay posture, target reachability |
| `GET /api/runtime/scorecard` | runtime telemetry + replay posture in one operator surface |
| `GET /api/replay-drift-board` | weakest replay areas stay visible instead of hiding behind the aggregate score |
| `GET /api/incident-command-board` | commander-facing triage of the riskiest replay cases |
| `GET /api/review-pack` | reviewer-first proof bundle and handoff contract |
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
- `docs/` — architecture, executive summary, discovery notes, and flagship review guide
- `infra/` — deployment drafts for discussion (`aws/` and `terraform/`)

## Repo map

```text
app/                     target API used by the local probe loop
aegis_engine/            structured RCA engine, replay/eval logic, runtime surfaces
frontend/                reviewer console + recorded demo payloads
tests/                   regression coverage for routes and review surface contracts
scripts/                 replay runner and runtime helpers
infra/                   restricted-environment deployment drafts
prometheus/              local metrics scrape config
docs/                    reviewer-facing architecture and proof docs
```

## Local run

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
- `GET /api/runtime/brief`
- `GET /api/runtime/scorecard`
- `GET /api/replay-drift-board`
- `GET /api/incident-command-board`
- `GET /api/review-pack`
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

## Supporting docs

- Flagship review guide: [`docs/FLAGSHIP_REVIEW_GUIDE.md`](docs/FLAGSHIP_REVIEW_GUIDE.md)
- Overhaul plan: [`docs/FLAGSHIP_OVERHAUL_PLAN.md`](docs/FLAGSHIP_OVERHAUL_PLAN.md)
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
