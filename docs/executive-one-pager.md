# Aegis-Air Executive One-Pager

## Problem

Many teams cannot send incident telemetry to public APIs, but still need faster incident triage and review.

## What Aegis-Air changes

- keeps incident review local-first
- produces structured RCA with explicit severity and failure bucket
- uses replay proof to validate quality claims before wider rollout

## Buyer value

- safer adoption path for restricted environments
- faster initial RCA
- clearer handoff from local triage to operator action

## Key metrics

- replay pass rate
- incident classification accuracy
- time to first actionable RCA
- local review readiness by target/service

## Rollout

1. replay-only validation
2. local probe loop against one service
3. expanded local incident review with downstream handoff

## Best proof path

- `/api/runtime/brief`
- `/api/review-pack`
- `/api/evals/replays`
- `docs/solution-architecture.md`
