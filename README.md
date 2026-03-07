# Aegis-Air

Aegis-Air is a zero-trust incident review system for teams that cannot send production telemetry to public APIs. It probes a target service, classifies the incident locally, and emits a structured RCA with severity, failure bucket, evidence, and immediate actions. The repo also includes a checked-in replay suite so changes can be scored against fixed incidents instead of judged on a single demo path.

## Why this repo is stronger than a one-off demo

- Live probe loop: the engine samples a target API, captures probe evidence, and streams a structured incident report back to the console.
- Deterministic fallback: if Ollama is unavailable, the RCA still completes locally from grounded heuristics instead of failing open.
- Replay evals: four checked-in incidents cover four failure buckets with `32/32` rubric checks.
- Structured output: `/api/incidents/report` and `/webhook/alert` return machine-readable reports, not just raw text.
- Operator-facing UI: the frontend surfaces severity, failure bucket, confidence, evidence, actions, and replay quality signals in one screen.

## Architecture

1. `app/main.py`
   - Dummy e-commerce API with injected checkout failures and Prometheus metrics.
2. `aegis_engine/main.py`
   - FastAPI engine that runs the live probe loop, serves the frontend, and exposes replay/eval endpoints.
3. `aegis_engine/replay_evals.py`
   - Checked-in replay cases, failure taxonomy, structured RCA builder, and rubric scoring.
4. `frontend/*`
   - Local ops console for live incident review and replay suite visibility.
5. `infrastructure/aws/*`
   - Terraform drafts showing how the pattern could be deployed into AWS.

## Replay Suite

The replay suite currently covers four buckets:

- `dependency-outage`
- `dependency-timeout`
- `latency-saturation`
- `auth-regression`

Current checked-in result:

- `4` cases
- `32/32` rubric checks passed
- `100%` severity accuracy
- `100%` failure-bucket accuracy
- `100%` taxonomy coverage

Run it locally:

```bash
python scripts/run_replay_suite.py
```

More detail: [docs/INCIDENT_REPLAY_EVALS.md](docs/INCIDENT_REPLAY_EVALS.md)

## API surface

- `GET /health`
- `GET /api/meta`
- `GET /api/chaos/trigger`
- `POST /api/incidents/report`
- `POST /webhook/alert`
- `GET /api/replays`
- `GET /api/evals/replays`

Example response from `POST /api/incidents/report`:

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

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Terminal 1:

```bash
uvicorn app.main:app --port 8000
```

Terminal 2:

```bash
uvicorn aegis_engine.main:app --port 8001
```

Then open:

- `http://127.0.0.1:8001`

## Verification

```bash
python -m compileall -q .
pytest -q
python scripts/run_replay_suite.py
```

## Notes

- The live console is useful for a local walkthrough, but the replay suite is the main quality signal in the repo.
- `chaos_engine/chaos_mesh.py` remains as a CLI driver and now receives a real `rca_report` from `/webhook/alert`.
- Ollama is optional for the narrative stream. The structured report path does not depend on it.
