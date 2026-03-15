# Aegis-Air Flagship Overhaul Plan

## Starting point
- Existing UX audit improved from **82 / revise** to **91 / pass** after moving reviewer actions higher above the fold and adding a clearer first-step helper line.
- Non-regression rule: keep the current reviewer quick-path and proof-first incident-console posture intact while improving repo-level clarity and low-risk implementation quality.

## Scope
1. **README / docs**
   - Reframe the repo as a flagship portfolio artifact for AI engineer / solutions architect review.
   - Make the review path, trust boundary, and proof assets easier to scan in under two minutes.
2. **Proof surface**
   - Add a tighter reviewer-facing guide that maps the best proof order to concrete routes, files, and expected takeaways.
3. **UX / devex**
   - Add a lightweight local task runner / command surface so setup, run, replay, and verification paths are obvious.
4. **Repo metadata / hygiene**
   - Add missing repository metadata that should exist for a serious public artifact.
5. **Code quality (low-risk only)**
   - Tighten one small runtime-summary behavior where the current implementation can under-report event counts when the persisted log grows.
   - Add regression coverage before/with that cleanup.

## Planned passes
1. **Docs / reviewer story pass**
   - Rewrite or tighten README sections around value, proof path, architecture, and verification.
   - Add one concise reviewer guide for hiring-manager / engineer walkthroughs.
2. **Devex / metadata pass**
   - Add a small Makefile with setup, run, replay, test, and verify targets.
   - Add an explicit MIT LICENSE file to match project metadata.
3. **Code hygiene pass**
   - Fix runtime-store summary counting so aggregate event counts reflect the full persisted log, not only the recent-event window.
   - Add targeted tests for the runtime-store behavior.

## Acceptance criteria
- README is easier to skim and clearly communicates:
  - what Aegis-Air is
  - why it matters for target roles
  - what to review first
  - how to run and verify it locally
- Reviewer guide exists and maps proof path to concrete endpoints / files.
- `make` targets exist for the common local workflows without adding dependencies.
- LICENSE file is present and matches the declared MIT license.
- Runtime-store regression coverage exists for aggregate counts vs recent events.
- `python -m compileall -q .`, `python -m pytest`, and `python scripts/run_replay_suite.py` pass after changes.

## Risks / watchouts
- README changes can drift from actual route names or repo layout; verify against code after edits.
- Devex additions must stay dependency-free and avoid promising unsupported workflows.
- Runtime-store cleanup must preserve existing JSONL format and recent-events behavior while only correcting aggregate counting semantics.
