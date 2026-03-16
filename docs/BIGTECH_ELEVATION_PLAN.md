# Big-Tech Elevation Plan

## Hiring Thesis

Turn `Aegis-Air` into the canonical `air-gapped incident runtime` counterpart to `AegisOps`. The hiring story should be: this repo proves the same incident workflow can survive harder data-boundary constraints without becoming hand-wavy.

## 30 / 60 / 90

### 30 days
- Add an offline model posture board that shows local classifier mode, narrative mode, and replay dependence clearly.
- Add an install bundle plus bootstrap checklist for restricted environments.
- Add a local-vs-cloud comparison note that explains what is preserved, degraded, or intentionally removed.

### 60 days
- Add an air-gapped replay kit with baseline and improved model bundles under the same rubric.
- Add operator review flows for weak evidence and classification uncertainty.
- Add one deployment topology guide for laptop, secure enclave, and isolated service node paths.

### 90 days
- Add a restricted-environment case study from target probe to commander handoff without public API dependency.
- Add a drift board that highlights where the local-first path underperforms the cloud-connected counterpart.
- Add an artifact bundle that lets a reviewer inspect the entire flow offline.

## Proof Surfaces To Add

- `GET /api/offline-model-board`
- `GET /api/deployment-topology`
- `GET /api/local-vs-cloud-scorecard`
- `GET /api/offline-review-bundle`

## Success Bar

- The repo reads like a serious constrained-environment system, not a reduced demo.
- Reviewers can compare tradeoffs honestly against cloud-connected incident AI.
- The local-first story becomes a hiring advantage instead of a caveat.
