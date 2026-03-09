# Aegis-Air Discovery Guide

## Best-fit signals

- telemetry cannot leave the environment
- operators want structured incident review without cloud-first inference
- the buyer needs deterministic proof before enabling live probe workflows

## Discovery questions

1. What data must remain local?
2. Which target service is the safest first pilot?
3. What evidence must be preserved for downstream handoff?
4. Is replay proof required before live probe adoption?
5. Which failure buckets are most common today?

## Demo path

1. show `/health`
2. show `/api/runtime/brief`
3. show `/api/review-pack`
4. show `/api/evals/replays`
5. run one live incident or replay case

## Success criteria

- replay path is trusted first
- local target posture is understandable
- downstream handoff contract is explicit
- restricted-environment trust boundary is clear

## Follow-up artifacts

- `docs/solution-architecture.md`
- `docs/executive-one-pager.md`
- `docs/INCIDENT_REPLAY_EVALS.md`
