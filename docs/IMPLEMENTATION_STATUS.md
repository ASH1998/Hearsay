# Hearsay implementation status

Last validated: 2026-07-19

This is a progress ledger for `IMPLEMENTATION_PLAN.md`; it does not override the
Game Design Document or Hackathon Blueprint.

## Milestone 1 — Playable Foundation

Status: complete on the configured Windows development workstation

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
- Optimized React Three Fiber Greyhaven scene using curated GLBs for the inn,
  houses, market, docks, foliage, props, player, and animated residents.
- Graph-constrained waypoint movement through buttons or WASD/arrow keys,
  player interpolation, conversation camera easing, interaction prompts,
  responsive dialogue, day/evening lighting, rain, lightning, and thunder.
- OpenAPI export and generated TypeScript contracts.
- Reproducible asset extraction/optimization pipeline, CC0 attribution ledger,
  checksummed manifest, public-runtime sync, and tracked validation report.
- SQLAlchemy/Alembic persistence with players, versioned run snapshots,
  idempotent actions, and immutable event records.
- Bounded CockroachDB serializable transaction retries and optimistic run
  revisions, retaining the deterministic in-memory fallback.
- Windows `.env` compatibility for Cockroach Cloud's certificate and connection
  commands, plus isolated `hearsay_test` migration/test automation.

Validated:

- `scripts/doctor.ps1` passes with Node 22.14, pnpm 11.9, uv 0.11.15,
  repository-local Python 3.12.13, environment names, and source assets.
- Ruff, formatting, strict mypy, and the local API suite pass.
- The configured Cockroach Cloud cluster is healthy; the `hearsay` application
  database is at migration head.
- Two real CockroachDB integration tests pass against `hearsay_test`, proving
  durable repository recreation, idempotent action replay, concurrent commits,
  monotonic revisions, and complete event history.
- Asset validation passes with 16 runtime assets, 7.84 MB initial load, 7.85 MB
  full session, and 44 source draw calls—within every Milestone 1 budget.
- ESLint, strict TypeScript, Vitest, and the Next.js production build pass.
- Next.js production build emits the App Router `/` route and standalone server.
- Tracked Playwright coverage completes create → promise → confrontation → Pip
  rumor → refresh and restores the durable story state.
- Live visual inspection against the configured Cockroach Cloud application
  database passes at desktop and 390×844 mobile viewports.

The in-memory repository remains available only as an explicitly selected,
deterministic unit/browser-test fixture. Normal development and application
persistence use the user-managed Cockroach Cloud `hearsay` database; destructive
integration tests use only `hearsay_test`.

## Next implementation slice

1. Add the belief/version/active-memory schema and scoped 384-dimensional vector
   retrieval.
2. Persist provenance-preserving rumor transmissions and relationship effects
   in one serializable tick transaction.
3. Add structured model output with deterministic fixtures, safe fallbacks, and
   real Modal inference when configured.
4. Build the Historian lineage view and prove the scoped vector plan with
   CockroachDB `EXPLAIN`.
