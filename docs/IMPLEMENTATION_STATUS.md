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

## Milestone 2 — Memory Proof Spine

Status: in progress

Completed:

- CockroachDB propositions, holder-specific beliefs, immutable composite belief
  versions, a separate active-memory projection, gossip ticks,
  provenance-constrained transmissions, relationships, and retrieval traces.
- A 384-dimensional cosine vector index on `active_memories`, prefixed by exact
  run, holder, and status fields. Both cloud databases are at migration
  `20260719_0005`.
- Deterministic embedding fixtures/fallbacks with explicit model provenance;
  embedding generation occurs before the serializable write transaction.
- Marta’s promise writes a durable belief and social debt. Bram’s confrontation
  writes Bram’s firsthand version, Pip’s mutated version, the transmission edge,
  gossip tick, active projections, and relationship effects in the same action
  transaction.
- Holder-scoped vector candidate retrieval followed by confidence, salience,
  and source-trust reranking, with candidates and selections recorded in a
  retrieval trace.
- Gameplay memory APIs and a Town Historian panel showing Bram → Pip lineage and
  the exact recorded mutation.
- Typed rumor-retelling, dialogue, and contradiction inference contracts; a
  strict-schema Modal/OpenAI-compatible provider; a deterministic provider; and
  bounded retry/fallback handling with sanitized structured logs.
- Modal calls occur before the Cockroach transaction. Every rumor transmission
  now records provider, model, attempt count, latency, and whether/why a
  deterministic fallback was used; the Historian exposes that provenance.
- `HEARSAY_LLM_PROVIDER=auto` selects the configured Modal endpoint when all
  credentials exist and uses the deterministic provider when working offline.

Validated:

- Thirty-two local API tests pass, covering immutable versions, lineage, recall,
  repeated claims, strict output validation, retries, all three fallback
  operations, and service-level inference provenance.
- Three real Cockroach Cloud tests pass against `hearsay_test`, including
  384-dimensional vector storage, active-projection freshness, recall, complete
  foreign-key provenance, relationship writes, and retrieval traces.
- A real `EXPLAIN` plan is forced through
  `active_memories_retrieval_vector_idx`.
- The browser story now proves create → promise → confrontation → visible Pip
  rumor → visible Historian lineage → refresh.
- `doctor` verifies the configured `hearsay` database migration head, VECTOR
  function support, vector-index cluster setting, and scoped index presence
  without emitting credentials.
- A real structured rumor request passes against the configured Modal endpoint
  with `thinkingmachines/Inkling-NVFP4`; the closed semantic schema prevents
  unbounded model-generated fields.
- Ruff, formatting, strict mypy, ESLint, TypeScript, Vitest, the Next.js
  production build, and the Playwright signature story pass.

Remaining:

- Replace the deterministic embedding fallback in configured development with a
  real local embedding provider and optional Modal acceleration.
- Add contradiction policy, contested inputs, evidence links, and the signature
  concurrent conflicting-belief race.
- Implement the independently authenticated read-only Managed MCP Historian.

## Next implementation slice

1. Implement contradiction resolution and the concurrent conflicting-belief
   race without losing either source history.
2. Add evidence support/contradiction links and feed recalled beliefs into
   dialogue choices and relationship treatment.
3. Replace deterministic embeddings in configured development with the local
   384-dimensional model while retaining the test fallback.
4. Configure the read-only Managed MCP Historian allowlist and audit surface.
