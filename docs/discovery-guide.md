# Aegis-Air Discovery Guide

## Best-fit signals

Use Aegis-Air when:
- telemetry cannot leave the environment
- operators need structured incident review without cloud-first inference
- replay proof is required before enabling live probe workflows
- the buyer cares about trust boundary clarity as much as model output quality

## Discovery questions

1. What incident data must remain local?
2. Which service is the safest first target for a local probe loop?
3. What evidence must survive into downstream handoff or postmortem?
4. Is replay proof required before live probe adoption?
5. Which failure buckets matter most today: outage, timeout, saturation, or auth drift?
6. Who needs the first handoff artifact: an SRE, app owner, solutions team, or security reviewer?

## Fast demo path

1. show `/health`
2. show `/api/runtime/brief`
3. show `/api/summary-pack`
4. show `/api/evals/replays`
5. show `/api/runtime/scorecard`
6. run one live incident or recorded review

## Success criteria

- replay path is trusted before live-loop claims are made
- local target posture is understandable to someone new to the project
- downstream handoff contract is explicit
- restricted-environment trust boundary is clear
- it's clear what is recorded proof versus live runtime evidence

## Follow-up artifacts

- `docs/solution-architecture.md`
- `docs/executive-one-pager.md`
- `docs/INCIDENT_REPLAY_EVALS.md`
