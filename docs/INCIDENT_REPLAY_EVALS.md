# Incident Replay Evals

This repo includes replay cases so incident analysis can be regression-tested locally.

## What is being scored

Each replay case is converted into a structured incident report with:

- `severity`
- `failure_bucket`
- `summary`
- `supporting_evidence`
- `immediate_actions`

Each case is then scored across `8` rubric checks:

1. Severity match
2. Failure-bucket match
3. Summary term A present
4. Summary term B present
5. Evidence term A present
6. Evidence term B present
7. Action term A present
8. Action term B present

Across four cases, that produces `32` total rubric checks.

## Replay scenarios

| Case | Expected Severity | Expected Bucket | Main Signal |
| --- | --- | --- | --- |
| Checkout database connection lost | SEV1 | dependency-outage | 500s from a broken primary dependency |
| Redis timeout storm | SEV1 | dependency-timeout | high p95 + repeated upstream timeouts |
| Checkout CPU saturation | SEV2 | latency-saturation | service stays up but breaches latency SLO |
| Secret rotation auth drift | SEV2 | auth-regression | immediate 401/403 failures after credential change |

## Current result

- `4` cases
- `32/32` checks passed
- `100%` severity accuracy
- `100%` failure-bucket accuracy
- `100%` taxonomy coverage

## Use

- keep heuristic changes reviewable
- compare structured reports across revisions
- see which failure buckets are covered
- catch regressions without depending on a single demo run
