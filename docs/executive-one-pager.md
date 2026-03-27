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

## Best evidence path

1. `GET /api/runtime/brief`
2. `GET /api/summary-pack`
3. `GET /api/evals/replays`
4. `GET /api/runtime/scorecard`

## Role fit

### AI engineer
- local classification pipeline
- replay-backed regression proof
- structured RCA contract with deterministic fallback

### Solutions architect
- explicit trust boundary between target, engine, replay layer, and dashboard
- restricted-environment deployment discussion via `infra/`
- clear separation of recorded review vs live probing

### Field / solutions engineer
- user-friendly walkthrough
- evidence surfaces shaped for handoff
- local console that preserves the incident story from replay to commander brief

## Rollout path

1. replay-only validation
2. local probe loop against one target service
3. summary pack + scorecard for internal trust building
4. operator-token and deployment hardening for restricted environments

## Current proof snapshot

- 4 replay cases
- 32 / 32 rubric checks passed
- severity labels matched expected outputs across all 4 replay cases
- failure-bucket labels matched expected outputs across all 4 replay cases
- taxonomy coverage stayed complete for the bundled replay set
