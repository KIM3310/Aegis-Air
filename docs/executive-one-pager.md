# Aegis-Air Executive One-Pager

## What it is

Aegis-Air is a **local-first incident-review engine** for teams that cannot send production telemetry to public APIs.

It probes a target service, classifies the failure locally, and produces a structured incident report with:
- severity
- failure bucket
- supporting evidence
- operator questions
- immediate actions

## Why it matters

Many incident demos break trust in restricted environments because they assume:
- cloud-hosted inference
- permissive data movement
- or a fake live dashboard

Aegis-Air is useful precisely because it does **not** assume those things.

## Core value

- **Local-first review:** telemetry stays in the operator environment
- **Deterministic proof:** replay cases validate severity and bucket logic before wider rollout
- **Handoff-ready output:** schema-backed incident reports stay usable even when narrative generation is unavailable
- **Honest review mode:** recorded-review surfaces remain explicit when the live engine is absent

## Best proof path

1. `GET /api/runtime/brief`
2. `GET /api/review-pack`
3. `GET /api/evals/replays`
4. `GET /api/runtime/scorecard`
5. `docs/FLAGSHIP_REVIEW_GUIDE.md`

## Role fit

### AI engineer
- local classification pipeline
- replay-backed regression proof
- structured RCA contract with deterministic fallback

### Solutions architect
- explicit trust boundary between target, engine, replay layer, and reviewer surface
- restricted-environment deployment discussion via `infra/`
- clear separation of recorded review vs live probing

### Field / solutions engineer
- reviewer-first walkthrough
- proof surfaces shaped for handoff
- local console that preserves the incident story from replay to commander brief

## Rollout path

1. replay-only validation
2. local probe loop against one target service
3. reviewer pack + scorecard for internal trust building
4. operator-token and deployment hardening for restricted environments

## Current proof snapshot

- 4 replay cases
- 32 / 32 rubric checks passed
- 100% severity accuracy
- 100% failure-bucket accuracy
- 100% taxonomy coverage
