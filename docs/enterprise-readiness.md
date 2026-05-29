# Enterprise Readiness Notes - Aegis-Air

Updated: 2026-05-30

This repository is archived. It can still support enterprise conversations as evidence of a pattern, playbook, or revival path, but production readiness requires a fresh pilot scope.

## Scope

| Field | Notes |
|---|---|
| Repository | `Aegis-Air` |
| Status | Archived supporting proof |
| Lane | Air-gapped incident review and RCA proof |
| Primary reader or buyer | Regulated SRE, security operations, platform reliability, and systems integrator teams. |
| Stack | Python, Terraform, Cloudflare, Docker |
| Readiness posture | Reviewable archive; revival requires updated dependencies, data handling, identity, monitoring, and support ownership. |

## Enterprise Controls

| Control | Current expectation |
|---|---|
| Data boundary | Public review should use synthetic, sample, or template data. Customer data requires a new retention, consent, access, and redaction review. |
| Identity and access | Any revived pilot needs named users, least privilege, SSO or scoped credentials where appropriate, and documented access review. |
| Auditability | Keep README status, CI, proof artifacts, generated reports, and handoff notes reviewable. |
| Observability | A revived pilot needs health checks, logs, failure states, cost or usage tracking, and owner-visible alerts. |
| Release gate | Full local gate: make verify; Test suite: make test |
| Support handoff | Name the owner, escalation path, known limits, rollback plan, and review cadence before presenting this as a maintained service. |

## Verification Surface

| Purpose | Command |
|---|---|
| Full local gate | `make verify` |
| Test suite | `make test` |

## CI Surface

- .github/workflows/architecture-blueprint.yml
- .github/workflows/ci.yml
- .github/workflows/dependency-review.yml
- .github/workflows/repository-health.yml
- .github/workflows/repository-surface.yml
- .github/workflows/secret-scan.yml

## Revival Path

- Confirm the current active successor or portfolio lane this repository supports.
- Run the documented local or CI checks and update dependencies if the code will be reused.
- Replace demo assumptions with buyer-approved data boundaries and acceptance criteria.
- Add identity, monitoring, audit, support, and rollback controls before a paid or production pilot.

## Proof Points

- Replay suite remains runnable
- Trust boundary is visible in README and API surfaces
- AegisOps relationship is clearly explained

## Open Risks

- Do not claim live telemetry access in the public demo
- Keep local-first boundaries explicit
- Frame as supporting proof, not the active flagship
