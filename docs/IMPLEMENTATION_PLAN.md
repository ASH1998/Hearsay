# Hearsay — End-to-End Implementation Plan

## Goal Contract

Build a complete, locally runnable browser game for the CockroachDB AI Hackathon: a polished 20–30 minute social-memory mystery set in Greyhaven during a mayoral election. The deliverable must demonstrate durable, evolving NPC memory in CockroachDB, vector retrieval, and a managed MCP integration, while remaining ready for the user to deploy manually to AWS later.

Continue autonomously until all local acceptance tests pass and the local deployment/submission handoff is complete. Make reasonable implementation decisions consistent with this document and the controlling project docs. If an optional capability is unavailable, implement and test a safe local fallback rather than stopping; only external credentials, account actions, or missing user-supplied assets may remain as documented manual work.

This plan does **not** authorize cloud provisioning, production deployment, GitHub push, or Devpost submission. All code, assets, generated artifacts, caches, and documentation remain inside this repository. Preserve existing user files, never inspect or print secret values, and make local milestone commits only after their gates pass. Completion excludes AWS deployment, public video upload, human playtesting, GitHub publication, and Devpost submission.

## Source-of-Truth Order

1. `docs/Hearsay_Game_Design_Document.md` governs the game, player experience, content, scope, and presentation.
2. `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs hackathon requirements, CockroachDB/AWS architecture, memory proof, MCP, and benchmarks.
3. For a conflict about the game, the game-design document wins. For a sponsor, technical, or compliance conflict, the blueprint and official hackathon rules win.
4. `AGENTS.md` and `PROJECT_MEMORY.md` record these decisions for future agents.

## Product Scope

- One browser-based 3D game: **Hearsay**.
- Three game days, six consequential actions per day, plus free movement and eavesdropping.
- Eight principal NPCs and twelve ambient NPCs.
- Twelve Greyhaven locations.
- Two dynamic town events: a storm and a public argument.
- Promises, favors, rumor mutation/lineage, per-person relationships, six public traits, speech bubbles, notice board, Town Ledger, day/night cycle, persistent returns, and memory-driven dialogue.
- A 20-vote mayoral election against Rhea, with a 10–10 tie resolving in Rhea’s favor.
- Six meaningful endings.
- A compressed but complete game, not an open-ended simulation. Movement, observation, and reading the notice board are free actions.

## Architecture

```text
Next.js / React Three Fiber browser client
        |
        | REST + WebSocket
        v
FastAPI game API ---- background worker / supervisor
        |                     |
        |                     +-- Modal LLM adapter during development
        |                     +-- Amazon Bedrock adapter for later production
        v
CockroachDB
  - durable game state
  - immutable memory provenance
  - active-memory vector index
  - retrieval/evaluation traces
  - benchmark evidence
        |
        +-- narrowly allowlisted Managed MCP operations
```

### Frontend

- Next.js application in `apps/web`.
- TypeScript, React Three Fiber, Drei, Three.js, Zustand, TanStack Query, Zod, and generated/OpenAPI client types.
- Lazy-loaded GLB environments, compressed textures, responsive UI, keyboard/mouse controls, subtitle and accessibility settings.
- Use a pnpm workspace and Next.js App Router. Generate the TypeScript client from FastAPI OpenAPI rather than duplicating contracts; Zustand is only for transient rendering/UI state while server snapshots remain authoritative.
- The client renders game state; it does not decide lore, memory, voting, or authoritative outcomes.

### Backend

- FastAPI application in `apps/api` using Python 3.12.
- SQLAlchemy, Alembic, psycopg 3, pgvector, Pydantic Settings, structured logging, and an explicit domain/service layer.
- LLM provider interface with:
  - Modal/OpenAI-compatible provider using the existing repository adapter and `thinkingmachines/Inkling-NVFP4` for development.
  - Amazon Bedrock Converse structured-output adapter for future deployment, configured for a Claude principal model and Nova Lite ambient work.
- BGE-small-en-v1.5 embeddings (384 dimensions), cached locally during development and stored per memory record.
- Dialogue, intent extraction, rumor retelling, contradiction analysis, and decision explanation use this provider interface.
- LLM and embedding calls occur outside database transactions; strict-schema validated results are committed afterward. Invalid, unavailable, or timed-out model work uses deterministic content-safe fallbacks and logs the reason.

### Project CockroachDB Instance

- Hearsay uses the user-managed Cockroach Cloud instance configured in the
  repository's ignored `.env` through `command_to_create_cert`,
  `command_to_connect`, `username`, and `password` (or an explicit
  `DATABASE_URL`).
- The application database on that instance is `hearsay`. Destructive
  integration tests are restricted to the separate `hearsay_test` database.
- `pnpm db:migrate` creates/migrates `hearsay`; `pnpm db:test` creates/migrates
  and validates only `hearsay_test`. Both commands support the supplied
  Cockroach Cloud certificate flow on Windows.
- Do not add or use a local CockroachDB Docker container as the normal
  development or test database. Keep credentials in `.env` only and never copy
  them into source, generated artifacts, logs, or documentation.

### Memory Model

The game will store facts as provenance-preserving records and maintain a retrieval-efficient active projection.

- `game_runs`, `players`, `characters`, `locations`, `schedules`, `events`, `messages`, `npc_profiles`, `relationships`, and `traits`.
- `beliefs` and immutable `belief_versions` for source, confidence, and change history.
- `active_memories` contains the currently active representation for each holder and is the vector-search target.
- `active_memories` includes `game_run_id`, `holder_id`, state, text, embedding `VECTOR(384)`, belief/version references, confidence, and timestamps.
- Its vector index uses equality-prefix fields such as run and holder so CockroachDB can perform appropriately scoped retrieval.
- `actions`, `conversations`, `propositions`, `promises`, `favors`, `transmissions`, `rumor_spread`, `votes`, `vote_inputs`, `vote_intentions`, `tick_jobs`, `decisions`, `telemetry`, `town_ledger_entries`, `retrieval_traces`, `llm_traces`, and `benchmark_runs` provide the full game and proof trail.
- Update active memory, belief pointers, transmissions, relationship consequences, and decision inputs together in a serializable transaction with bounded SQLSTATE `40001` retries.
- Every transmission has source lineage, every active memory points to an immutable version, and every decisive vote retains explainable inputs.

## Repository Bootstrap and Local Tooling

Before the first commit, replace the existing one-line `.gitignore` and create `.gitattributes`, `.env.example`, MIT `LICENSE`, `THIRD_PARTY_ASSETS.md`, root `package.json`, `pnpm-lock.yaml`, `.npmrc`, `pyproject.toml`, and `uv.lock`.

1. Create the monorepo directories: `apps/web`, `apps/api`, `packages`, `infra`, `scripts`, `tests`, `assets`, `docs`, and `tools`.
2. Install a standalone pinned `uv` executable under `tools/uv`; record its version and checksum in project documentation.
3. Configure repository-local tool paths so no build output is written to a user profile:

   ```text
   UV_PROJECT_ENVIRONMENT=.venv
   UV_PYTHON_INSTALL_DIR=tools/python
   UV_CACHE_DIR=.cache/uv
   UV_TOOL_DIR=tools/uv-tools
   HF_HOME=.cache/huggingface
   TORCH_HOME=.cache/torch
   PLAYWRIGHT_BROWSERS_PATH=.cache/ms-playwright
   ```

4. Use `tools/uv/uv.exe python install 3.12`, then create `.venv` with Python 3.12. The installed system Python 3.13 is not the project runtime.
5. Define Python dependencies in `pyproject.toml` and synchronize them using `tools/uv/uv.exe sync --all-groups`.
6. Pin Node 22 and `pnpm@11.9.0` via `packageManager`. Use pnpm for the frontend; add `.npmrc` with a repository-local `.pnpm-store` and keep `node_modules` inside the repository.
7. Add portable, optional tools under `tools/` only when needed: Blender for asset conversion and `ccloud` for later Cockroach Cloud administration. Verify downloaded tools by checksum.
8. Add idempotent PowerShell and POSIX `bootstrap`, `doctor`, `dev`, `test`, and `assets` scripts. Bootstrap installs tools, Python, `.venv`, dependencies, and Playwright then validates assets. Doctor checks tool versions, non-secret environment-variable names, the configured Cockroach Cloud connectivity/vector support, Modal structured output, assets, and ports. Test runs unit, integration, browser, benchmark-smoke, formatting/type, and secret checks. Assets extracts, curates, optimizes, validates, and reports runtime sizes.
9. Use the user-provided Cockroach Cloud instance for development and sponsor-specific integration tests. Maintain separate `hearsay` and `hearsay_test` databases and do not require Docker for the application or database workflow.

### Planned Dependencies

Python: FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy, Alembic, psycopg, pgvector, boto3, OpenAI, sentence-transformers, HTTPX, MCP client support, structlog, pytest, pytest-asyncio, Hypothesis, Ruff, mypy, and coverage tooling.

Node: Next.js, React, TypeScript, React Three Fiber, Drei, Three.js, Zustand, TanStack Query, Zod, OpenAPI tooling, glTF Transform, Vitest, Playwright, ESLint, and formatting/type-check tooling.

## Version-Control Hygiene

Create a comprehensive `.gitignore` that ignores:

- Secrets and certificates: `.env`, `.env.*`, `*.pem`, `*.key`, certificates, and local credential files, while retaining `!.env.example`.
- Python environments and artifacts: `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, coverage data, `dist`, `build`, and `*.egg-info`.
- Node artifacts: `node_modules`, `.pnpm-store`, `.next`, `out`, `.turbo`, package-manager logs, and generated reports.
- Test results: Playwright output, screenshots, videos, and temporary snapshots.
- Repository-local caches and downloaded tool binaries: `.cache`, `tools/uv`, `tools/python`, and `tools/uv-tools`.
- Raw/intermediate asset locations: `assets/downloads`, `assets/source`, `assets/work`, `assets/tmp`, `assets/render-cache`, and `assets/processed/debug`.
- Runtime state: logs, temporary data, replay scratch files, generated benchmark output, and local database volumes.
- Infrastructure state: Terraform state, plan output, CDK output, and local deployment overrides.
- OS and editor noise.

Do **not** ignore migrations, source assets selected for runtime, asset manifests/licenses, processed production assets, content data, test fixtures, frozen benchmark fixtures, documentation, or future AWS deployment templates.

Add `.gitattributes` to place runtime binary assets such as `*.glb`, `*.ktx2`, large `*.webp`, and `*.ogg` files in Git LFS once the repository is ready to track them.

The actual `.gitignore` must include this complete baseline, not merely broad patterns:

```gitignore
# Secrets and certificates
.env
.env.*
!.env.example
*.pem
*.key
*.crt
*.cer
*.p12
*.pfx
credentials/
secrets/
certs/

# Python
.venv/
__pycache__/
*.py[cod]
*.pyd
*.so
.pytest_cache/
.mypy_cache/
.ruff_cache/
.hypothesis/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
build/
dist/
*.egg-info/

# Node and Next.js
node_modules/
.pnpm-store/
.next/
out/
.turbo/
.eslintcache
npm-debug.log*
pnpm-debug.log*
yarn-debug.log*
yarn-error.log*

# Tests, local tools, and caches
coverage/
playwright-report/
test-results/
blob-report/
.cache/
tools/uv/
tools/python/
tools/uv-tools/
tools/blender/
tools/ccloud/
tools/bin/

# Raw and intermediate assets
assets/downloads/
assets/source/
assets/work/
assets/tmp/
assets/render-cache/
assets/processed/debug/

# Runtime scratch data
logs/
*.log
tmp/
.temp/
data/local/
replays/tmp/
benchmarks/tmp/
reports/generated/

# Infrastructure state
**/.terraform/
*.tfstate
*.tfstate.*
crash.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
cdk.out/

# Editors and operating systems
.vscode/
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db
Desktop.ini
```

Keep raw ZIPs and portable tools locally inside the repository but untracked. Commit curated runtime assets, source URLs, checksums, licenses, and reproducible processing scripts. Run a secret scan before the initial commit and after every milestone, without reading or emitting secret values.

## Asset Pipeline

1. Inventory every asset in `assets/downloads`; retain source/license metadata in an asset manifest.
2. Extract raw downloads into ignored `assets/source` and create only selected, optimized runtime assets in tracked `assets/processed`.
3. Use Quaternius Medieval Village, Stylized Nature, Fantasy Props, Universal Base Characters, Character Outfits, and Universal Animation Library as the visual foundation.
4. Use only selected Pirate Kit glTF props for the dock area: dock pieces, anchor, barrels, bottles, bucket, fish, and related neutral set dressing. Exclude pirate characters, ships, cannons, skeletons, tropical scenery, treasure, and other out-of-place assets.
5. Use Kenney UI Adventure and UI Audio under their CC0 terms for interface and feedback audio.
6. Build reproducible Blender/glTF Transform scripts for twenty shared-rig character variants, selected animations, portraits, consistent GLB conversion, removal of unused materials/animations, LODs as appropriate, meshopt/draco compression, and KTX2/Basis texture compression.
7. Produce a manifest with source, license, use, processed output, size, and checksum for every runtime asset.
8. Enforce initial-load and full-session budgets: initial scene at or below 25 MB, full session at or below 60 MB, roughly 300 draw calls or fewer, and playable 30 FPS on an integrated GPU.

## Game Implementation Order

### Milestone 1 — Playable Foundation

- Scaffold frontend, backend, tests, Cockroach Cloud configuration, and developer scripts.
- Build an optimized inn, square, and docks scene with a controllable player, collision, camera, three animated NPCs, interaction prompts, speech bubbles, dialogue panel, day/evening lighting, rain, and save/load run creation.
- Prove the browser client can create a run, take an action, and receive authoritative state from the API.
- Add the asset manifest and attribution page.
- Gate: a clean bootstrap succeeds and the browser asset proof produces a size/asset validation report.

### Milestone 2 — Memory Proof Spine

- Create all CockroachDB migrations and seed data.
- Implement action processing, immutable memory versions, active-memory projection, embeddings, scoped vector retrieval, and retrieval traces.
- Implement structured LLM outputs with schema validation, graceful fallback dialogue, and deterministic test-provider fixtures.
- Build the signature loop: promise Marta help, confront Bram, Pip mutates the story, treatment changes, and the Historian reconstructs the chain.
- Add representative tests for a rumor being learned, contradicted, revised, retrieved by the right NPC, and affecting a future response.
- Add a Historian view that explains why an NPC believes a specific claim.
- Gate: real Modal inference and a real Cockroach vector query with `EXPLAIN` when configured; deterministic fixtures provide equivalent local coverage otherwise. Refresh-safe restoration and complete lineage are mandatory.

### Milestone 3 — Full Compressed Game

- Implement all twelve locations, three daily schedules, eight principal NPC arcs, twelve ambient NPC behaviors, and free movement/eavesdropping. The schedule checkpoint now defines all 20 residents across three days and four daily phases, applies movements in the authoritative action transition, persists public movement events and the resulting snapshot in the configured Cockroach Cloud database, and renders restored positions directly from that state.
- Add the 18 consequential actions, promises, favors, rumor propagation, relationship changes, trait effects, storm, public argument, and election calculation. The opening Bram choice now implements threaten/flatter/negotiate/lie as distinct content-driven actions, memories, Pip mutations, relationship/trait consequences, and belief-backed vote inputs; seeded normal-play paths reach both Exposed and Run out of town. The never-cut storm now ships with durable begin/clear state, rain/lightning/thunder/warm-window rendering, a full-inn schedule override, event-aware dialogue, refresh restoration, and real Cockroach event-row proof. The Day 2 public argument now adds square crowd staging, mutual faction damage, three one-shot interventions, holder-specific immutable memories, and audited downstream vote effects.
- Write content as data rather than embedded code; include validation that every referenced NPC, location, action, memory, and ending exists.
- Implement the six endings and replay-safe save/resume behavior.
- Gate: seeded full win and loss playthroughs complete without manual database repair or developer-console intervention.

### Milestone 4 — Hackathon Evidence

- Implement a read-only, server-side MCP integration with a narrow allowlist and audit log. Never expose Cockroach credentials to the browser.
- Add a Director/Historian interface for inspecting turns, memories, sources, confidence, retrieval context, revisions, and downstream outcomes.
- Build benchmark fixtures for memory retrieval, contradiction handling, latency, and deterministic replay.
- Capture query plans and evidence demonstrating the vector index and scoped retrieval are used correctly.
- Add rumor graph/mutation diffs, vote explanations, a concurrent-update race proof, cost telemetry, replay bundles, and a three-arm benchmark.
- Build a narrow supervisor that can restart only the gossip child process, then automatically audit partial state.
- Create a concise architecture diagram, demo walkthrough, and judging-evidence checklist.
- Gate: zero orphan transmissions, zero unlinked belief versions, zero stale active memories, and Historian explanations for decisive votes.

### Milestone 5 — Quality and Handoff

- Run formatting, linting, type checks, unit tests, integration tests, browser tests, asset-budget checks, content validation, and benchmark tests.
- Run seeded automated win, loss, and rumor-driven playthroughs; human playtesting remains a post-Goal manual task.
- Produce deployment-ready but unapplied native EC2 service, S3/CloudFront, IAM, parameter/secret, and Bedrock configuration templates sized for the user’s 2 vCPU / 4 GB EC2 instance.
- Finalize README, setup instructions, `.env.example`, architecture notes, licensing/attribution, operations runbook, benchmark report, feedback template, Devpost draft copy, and under-three-minute demo-video storyboard/script.

## APIs and Runtime Contracts

- `POST /v1/runs` creates a new game run.
- `GET /v1/runs/{id}/snapshot` returns the authoritative state needed by the client.
- `POST /v1/runs/{id}/actions` validates and resolves player actions.
- `GET /v1/runs/{id}/memories` returns immutable belief versions and
  provenance-linked rumor transmissions for the gameplay Historian view.
- `POST /v1/runs/{id}/memories/recall` performs holder-scoped vector retrieval,
  relational reranking, and records a retrieval trace.
- `POST /v1/runs/{id}/historian/trace` reconstructs one allowlisted proposition
  through the official CockroachDB Cloud Managed MCP `select_query` tool when
  independently authenticated. Its response includes a durable audit envelope;
  `sponsor_proof=true` is impossible on a direct-database or in-memory fallback.
- `GET /v1/runs/{id}/election` returns the resolved 20-vote tally, ending,
  per-voter score, every deterministic input, top-three decisive inputs, and
  exact belief/version references. Before midnight it returns a conflict rather
  than predicting or fabricating a result.
- WebSocket stream delivers state transitions, NPC reactions, and dialogue events.
- Historian endpoints expose redacted, explainable memory provenance and retrieval traces.
- Director endpoints are token-protected, provide test/demo controls only when explicitly enabled in development, and are never exposed as a public gameplay surface.
- The Historian uses the official Managed MCP Server at
  `https://cockroachlabs.cloud/mcp` through a server-side allowlist. The first
  implemented operation invokes only `select_query`; future schema and plan
  operations may add only the documented read tools. Discovered write tools are
  never callable through the Historian. The independently supplied cluster ID
  and API key never reach the browser, logs, query text, or audit rows.
- `HEARSAY_HISTORIAN_PROVIDER=managed_mcp` fails closed when independent MCP
  credentials or the read tool are unavailable. `auto` may retain a playable
  direct-Cockroach fallback, but both the API and browser label it
  `not MCP proof`, store the reason, and set `sponsor_proof=false`.

## Quality Gates

- Unit tests for election mathematics, promise/favor resolution, traits, rumor constraints, schedules, idempotency, seed data, memory revision, relationship deltas, retrieval ranking, and content validation.
- Integration tests use the isolated `hearsay_test` database on the configured Cockroach Cloud instance; deterministic unit and browser fixtures may use the in-memory repository, but no disposable container database is introduced. Cockroach-specific coverage includes migrations, vector-index use, retries, concurrent updates, MCP allowlisting, worker recovery, Town Ledger isolation, provider contracts, and replay determinism.
- Property tests for state-machine invariants and replay stability.
- Playwright tests for onboarding, broken-promise propagation, rumor travel, storm refresh, reconnect, full election, ending classes, two isolated runs, Director’s Room, and one full game path.
- Benchmark tests that write reproducible evidence rather than relying on a one-off demonstration.
- A failure mode never silently changes game state: invalid model output, unavailable embedding model, unavailable LLM, or retrieval failure falls back safely and is logged.
- Clean-machine acceptance consists of the documented bootstrap command followed by `doctor`, `test`, and `dev`, without a global Python dependency.

## Manual Deployment Handoff (Not Executed by This Goal)

1. User keeps using the existing Cockroach Cloud instance configured in `.env` and provisions only the remaining EC2, S3/CloudFront, IAM, and Bedrock resources.
2. User supplies deployment secrets through the documented environment/parameter mechanism.
3. User deploys the prepared native EC2 services and static assets using the provided runbook; Hearsay does not require Docker for its database or application workflow.
4. User verifies a public demo, records the demo video, pushes the public repository, and submits before the hackathon deadline.
5. Keep the demo available through the judging period.

## Definition of Done

- A new contributor can run one bootstrap command, create `.venv`, install dependencies, and start the browser game locally.
- The full 20–30 minute Greyhaven election story is playable and saves/resumes correctly.
- NPC behavior visibly changes because of stored, retrieved, revised, and explainable memories.
- The repository contains automated proof for CockroachDB persistence/vector retrieval, the MCP integration, AWS-ready deployment, assets, licensing, tests, benchmark evidence, and hackathon submission materials.
- No secrets, local caches, raw asset downloads, or generated development artifacts are committed.
