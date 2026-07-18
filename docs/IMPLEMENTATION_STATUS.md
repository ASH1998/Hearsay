# Hearsay implementation status

Last validated: 2026-07-19

This is a progress ledger for `IMPLEMENTATION_PLAN.md`; it does not override the
Game Design Document or Hackathon Blueprint.

## Milestone 1 — Playable Foundation

Status: in progress

Completed:

- Repository hygiene: comprehensive ignore rules, Git LFS attributes, MIT
  license, environment template, attribution ledger, and local tool records.
- Pinned repository-local `uv` 0.11.15 and CPython 3.12.13 bootstrap.
- pnpm 11.9 workspace with a locked Next.js 16 / React 19 frontend.
- FastAPI create-run, snapshot, action, and WebSocket contracts.
- Idempotent authoritative actions with a deterministic development repository.
- Twelve Greyhaven locations and all eight principal NPCs stored as validated
  content data.
- Playable Marta promise → Bram confrontation → Pip rumor tick.
- Compact React Three Fiber town proof with day-phase lighting, resident
  markers, speech bubbles, interaction panels, clock, ledger, and waypoints.
- OpenAPI export and generated TypeScript contracts.
- Empty-but-valid runtime asset manifest with 25 MB initial and 60 MB session
  budgets.
- SQLAlchemy/Alembic persistence with players, versioned run snapshots,
  idempotent actions, and immutable event records.
- Bounded CockroachDB serializable transaction retries and optimistic run
  revisions, retaining the deterministic in-memory fallback.
- Windows `.env` compatibility for Cockroach Cloud's certificate and connection
  commands, plus isolated `hearsay_test` migration/test automation.

Validated:

- `scripts/doctor.ps1` passes with Node 22.14, pnpm 11.9, uv 0.11.15,
  repository-local Python 3.12.13, environment names, and source assets.
- Ruff, formatting, strict mypy, and seventeen local API tests pass.
- The configured Cockroach Cloud cluster is healthy; the `hearsay` application
  database is at migration head.
- Two real CockroachDB integration tests pass against `hearsay_test`, proving
  durable repository recreation, idempotent action replay, concurrent commits,
  monotonic revisions, and complete event history.
- ESLint, strict TypeScript, and Vitest pass.
- Next.js production build emits the App Router `/` route and standalone server.
- Local browser smoke test completes the opening promise and confrontation,
  shows Pip's changed rumor, reaches tick 1 / Day 1 afternoon, reports no browser
  console errors, and restores that state after refresh.

Remaining before the Milestone 1 gate:

- Curate and optimize the inn, square, docks, three character variants,
  animation clips, UI audio, and environment audio from the candidate archives.
- Replace proxy geometry with lazy-loaded GLB runtime assets.
- Add keyboard player movement, waypoint collision, conversation camera easing,
  rain/thunder, and animated residents.
- Add Playwright automation and produce the tracked asset validation report.
- Expand the durable schema from run snapshots into beliefs, immutable belief
  versions, active vector memories, relationships, promises, transmissions,
  votes, traces, and benchmark evidence.

## Next implementation slice

1. Build the reproducible asset inventory/extraction pipeline without committing
   raw archives.
2. Add the belief/version/active-memory schema and scoped 384-dimensional vector
   retrieval.
3. Persist provenance-preserving rumor transmissions and relationship effects
   in one serializable tick transaction.
4. Add a browser test for create → promise → confront → rumor → refresh.
