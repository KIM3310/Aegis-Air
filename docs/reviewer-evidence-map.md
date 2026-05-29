# Review Guide - Aegis-Air

Updated: 2026-05-30

This repository is archived as a supporting proof. Review it for the reusable pattern, domain evidence, and portfolio relationship; do not treat it as the current flagship unless it is explicitly revived.

## Summary

| Field | Notes |
|---|---|
| Repository | `Aegis-Air` |
| Status | Archived supporting repository |
| Lane | Air-gapped incident review and RCA proof |
| Primary reader | Regulated SRE, security operations, platform reliability, and systems integrator teams. |
| Why it exists | Teams with strict telemetry boundaries still need structured incident evidence and replay-backed RCA. |
| Stack | Python, Terraform, Cloudflare, Docker |

## Open First

1. Read the README archived-status note and relationship to active repositories.
2. Inspect `docs/monetization-playbook.md` for the buyer lane and offer ladder.
3. Use the commands below to confirm the proof surface still has a review path.
4. Check CI workflows before making quality claims.
5. Keep the archived status visible in any portfolio conversation.

## Checks

| Purpose | Command |
|---|---|
| Full local gate | `make verify` |
| Test suite | `make test` |

## CI

- .github/workflows/architecture-blueprint.yml
- .github/workflows/ci.yml
- .github/workflows/dependency-review.yml
- .github/workflows/repository-health.yml
- .github/workflows/repository-surface.yml
- .github/workflows/secret-scan.yml

## Evidence

- Replay suite remains runnable
- Trust boundary is visible in README and API surfaces
- AegisOps relationship is clearly explained

## Commercial Notes

| Possible offer | Working price assumption | Scope |
|---|---|---|
| Trust-boundary diagnostic | $5k-$15k | Map incident data movement, local model posture, and evidence gaps. |
| Restricted-environment pilot | $30k-$90k | Adapt the replay suite and RCA taxonomy to one production-like service. |
| Local incident review license | $120k+/year | Package the runtime, replay harness, and operator review workflow for internal use. |

## Boundaries

- Do not claim live telemetry access in the public demo
- Keep local-first boundaries explicit
- Frame as supporting proof, not the active flagship

## Useful Metrics

- Diagnostic requests
- Pilot conversion
- Replay coverage
- Time-to-RCA delta
