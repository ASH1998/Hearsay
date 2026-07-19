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
  `20260719_0008`.
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
- Durable `evidence`, `evidence_links`, and provenance-preserving
  `belief_inputs` record accepted, corroborated, contested, rejected, and
  needs-evidence claims independently from the one active belief pointer.
- A deterministic conflict policy compares source trust, evidence,
  corroboration, recency, and bias. Close contradictions preserve the current
  semantic position at reduced confidence and mark it contested; strong or weak
  claims cross explicit accept/reject margins.
- The Town Historian contract now includes every evaluated claim, the version it
  observed and actually evaluated, its outcome, resulting version, transaction
  attempts, and whether it was re-evaluated after a serialization conflict.
- Configured development now uses local `BAAI/bge-small-en-v1.5` through
  Sentence Transformers 5.6 on CPU. Stored memories use normalized passage
  embeddings; recall queries use the model-card retrieval instruction.
- Embedding results carry truthful provider/model/fallback provenance. A load,
  shape, or non-finite-value failure logs only its exception class and stores a
  deterministic `hearsay-hash-384-v1` vector instead of falsely claiming BGE.
- Model and Torch/Hugging Face caches remain under ignored repository paths;
  `THIRD_PARTY_MODELS.md` records the exact upstream model and MIT license.
- Player questions now run holder-scoped vector recall before dialogue
  generation. Contested memories are explicitly marked in the validated prompt,
  and the call still occurs before the authoritative action transaction.
- Saved dialogue state records the exact recalled belief/version references,
  contested flags, provider, model, and fallback status. The browser surfaces a
  “Memory-informed” audit label, and refresh preserves the complete response
  context.
- A retrieval failure logs only its exception class and preserves the authored
  NPC opening instead of fabricating or silently changing game state.
- Recalled memory now projects into idempotent per-NPC treatment thresholds:
  hostile rumor → Pip standing `-10` / trust ceiling `0.40`; contested account
  → Elias standing `-5` / trust ceiling `0.45`; remembered promise → Marta
  standing `+10` / trust floor `0.60`.
- Dialogue state carries a player-visible treatment cue and functional
  memory-conditioned follow-up chips. Thresholds are floors/ceilings rather than
  repeatable deltas, so repeated Talk actions cannot farm or destroy trust.
- Marta's shipment promise now resolves deterministically at its real deadline.
  A new Bram settlement action keeps it before evening; any still-active
  promise becomes broken as the clock enters evening.
- Kept and broken outcomes each append an immutable Marta belief version and a
  provenance-linked Marta → Pip public retelling in the same authoritative
  action transaction. The active projection therefore replaces "promised" with
  the observed outcome instead of leaving stale intent as memory.
- Promise outcomes also write idempotent trust floors/ceilings, visible Pip
  chatter, and deterministic public traits: kept → Reliable/Generous; broken →
  Dishonest/Troublemaker. Marta's later dialogue recalls the outcome and changes
  to grateful `+20` or bitter `-20` treatment with functional follow-ups.
- Cockroach action persistence now inserts every new visible event in one
  revision. When a deadline expires during another action, both the triggering
  conversation and the broken-promise event survive as separate immutable rows.
- A server-side Town Historian client now targets Cockroach Labs' official
  `https://cockroachlabs.cloud/mcp` Streamable HTTP endpoint with a separately
  supplied cluster ID and service-account API key.
- The first Historian operation is fixed to rumor lineage and may invoke only
  the advertised `select_query` tool. It discovers that tool's typed input
  schema, adapts only the database/query field names, rejects unknown required
  inputs, and rejects writes or multiple SQL statements before transport.
- Managed MCP lineage reads return the same validated immutable-version,
  transmission, and belief-input contract as direct repository inspection. MCP
  credentials, raw authorization headers, and the cluster ID are never returned
  or persisted; the audit stores only a one-way cluster fingerprint.
- Every Historian attempt writes a durable `historian_audits` row with provider,
  attempted provider, tool, authentication mode, fixed query ID, result counts,
  latency, success, and sanitized fallback class.
- The proof contract fails closed in forced `managed_mcp` mode. In `auto`, an
  unavailable or unconfigured MCP connection uses a conspicuously labeled
  fallback, with both API and UI forcing `managed_mcp=false` and
  `sponsor_proof=false`.

Validated:

- Fifty-nine local API tests pass, covering immutable versions, lineage, recall,
  repeated claims, strict output validation, retries, all three fallback
  operations, service-level inference provenance, and every deterministic
  conflict-policy branch, plus real-provider shape checks and truthful embedding
  fallback provenance.
- Six real Cockroach Cloud tests pass against `hearsay_test`, including
  384-dimensional vector storage, active-projection freshness, recall, complete
  foreign-key provenance, relationship writes, retrieval traces, evidence
  links, and contested inputs.
- One Cloud test proves a fallback Historian attempt is durably audited
  on the real cluster and cannot set the Managed MCP sponsor-proof bit.
- The sixth Cloud test advances a live run to the missed deadline and proves
  the action event, deadline event, immutable outcome memories, Marta → Pip
  transmission, traits, and trust ceiling commit coherently.
- A real `EXPLAIN` plan is forced through
  `active_memories_retrieval_vector_idx`.
- The browser story now proves create → promise → confrontation → visible Pip
  rumor → visible Historian lineage with an explicit “not MCP proof” fallback
  label → refresh.
- `doctor` verifies the configured `hearsay` database migration head, VECTOR
  function support, vector-index cluster setting, and scoped index presence
  without emitting credentials.
- A real structured rumor request passes against the configured Modal endpoint
  with `thinkingmachines/Inkling-NVFP4`; the closed semantic schema prevents
  unbounded model-generated fields.
- In the synchronized signature race, Marta and Bram both read Elias belief v4.
  One commits v5; Cockroach retries the other operation, which re-evaluates
  against v5 and commits v6. Both source inputs remain queryable, exactly one
  active memory remains, and Elias is durably marked contested.
- A real cached BGE CPU probe returns normalized 384-dimensional vectors and
  ranks a related shipment-price query above an unrelated chapel-weather query
  (`0.786` versus `0.354` in the latest doctor run).
- Local and real Cockroach tests prove Pip answers from his own mutated rumor,
  Elias answers from his contested active belief after the concurrent race, and
  the exact memory references survive snapshot restoration.
- The browser proof visibly changes Pip to standing `-10`, explains the cold
  treatment, and unlocks “Ask what they heard” / “Set the record straight.”
  Cloud tests prove repeated contested conversations leave Elias at the same
  `0.45` trust ceiling rather than applying another penalty.
- The browser proof now continues by paying Bram before evening, visibly marks
  the promise Kept, writes Reliable/Generous on the notice-board projection,
  changes Marta to `+20` grateful treatment, unlocks "Ask for endorsement," and
  restores that outcome after refresh.
- Ruff, formatting, strict mypy, ESLint, TypeScript, Vitest, the Next.js
  production build, and the Playwright signature story pass.

Remaining:

- Add `COCKROACH_MCP_CLUSTER_ID` and `COCKROACH_MCP_API_KEY` to the ignored
  `.env`, authorize that independent identity for read access, and capture a
  real successful Managed MCP `select_query` proof. The current `.env` has the
  SQL connection and Modal credentials but no MCP identity, so no real MCP
  success is claimed.

## Milestone 3 — Full Compressed Game

Status: in progress

Completed:

- Greyhaven content now defines all eight principals and twelve named ambient
  residents with roles, locations, openings, colors, and authored voter biases.
  The authoritative opening snapshot contains all 20, and the 3D renderer
  spaces co-located residents around their waypoint instead of stacking them.
- The content file defines all six GDD endings—Landslide, Narrow win, Narrow
  loss, Humiliation, Exposed, and Run out of town—and validation rejects a
  roster or ending set that violates the game contract.
- Day-two candidacy is a real consequential action. It cannot be declared early
  or repeated, is visible on the ballot projection, and persists through
  refresh.
- Midnight resolves a deterministic 20-vote election. A 10–10 tie explicitly
  stays with Rhea. The ending classifier gives public safety/exposure traits
  priority, then applies documented landslide/win/loss/humiliation thresholds.
- Every voter records their authored disposition, applicable public traits,
  direct relationship, and active memory inputs. Each input stores its weight,
  contribution, explanation, decisive rank, and exact belief/version reference
  where applicable.
- Migration `20260719_0008` adds one durable election, 20 immutable votes, and
  normalized vote-input rows. Election, votes, inputs, final snapshot, and the
  visible election event commit in the same serializable action transaction.
- `GET /v1/runs/{id}/election` fails with `409` before resolution and returns
  the complete explainable result afterward. The ending surface highlights
  memory-bearing decisive voters and shows contribution plus belief ID/version.
- Sleep/end-day is now a visible player action. A seeded promise-kept path
  compresses the full three-day arc into a reproducible `11–9` Narrow win.
- Validated content now assigns every resident to an authored three-day,
  morning/afternoon/evening/night schedule. Shared ambient templates keep the
  roster maintainable while principal residents retain individual routines.
- The authoritative action clock applies each phase transition to all 20 NPC
  locations. Every actual movement wave emits one public `schedule_shift`
  event, and the saved snapshot is the single source used by both the 3D scene
  and restored browser sessions.
- The action bar reports each principal's current location instead of a fixed
  opening location. The event strip exposes the three newest immutable events,
  so movement remains visible without hiding a promise or election consequence.
- The judge-critical Bram scene now offers all four GDD approaches: threaten,
  flatter, negotiate, or lie. Their labels, dialogue, visible events, claims,
  relationship deltas, traits, and election weights are validated content data.
- Each approach creates a distinct Bram firsthand belief and a distinct Pip
  retelling with immutable provenance. The active approach and its exact
  election contribution travel with the belief version into both voters'
  normalized decision inputs.
- Threatening derives Dangerous/Troublemaker and reaches the staged Run out of
  town ending; lying about Elias derives Dishonest and reaches Exposed. Both
  are seeded, normal-action playthroughs rather than classifier-only fixtures.
- The GDD's never-cut storm now has a durable lifecycle: it begins at Day 1
  evening, remains active through the night, resolves on Day 2 morning, and
  records both transitions even when Sleep skips across the whole interval.
- The storm satisfies the no-render-no-event rule. The renderer supplies rain,
  wet fog, lightning, synthesized thunder, darker ground, and warm window
  lights; the behavior layer evacuates all 20 residents into the inn; Marta,
  Nessa, and Pip receive authored active/resolved awareness lines.
- Active town-event state, weather, overridden resident positions, awareness,
  and public lifecycle events are server-authoritative. Refresh renders the
  restored Cockroach snapshot, and storm clearing reapplies the authored Day 2
  schedules instead of leaving stale crowd positions.
- Day 2 afternoon now starts the Bram–Nessa public argument. Its schedule
  override stages all 20 residents in a square ring, a visible scene banner
  identifies the confrontation, and Bram/Nessa/Pip receive active and resolved
  lines. Day 2 evening closes it and restores normal schedules.
- Starting the argument writes directional Bram→Nessa and Nessa→Bram trust and
  affinity damage. The Town Ledger exposes three authored interventions: back
  Bram, defend Nessa's crews, or calm the crowd; a run accepts exactly one.
- Each intervention changes both visible principal standings, derives any
  matching public trait, writes three holder-specific immutable memories, and
  carries the exact choice/contribution/belief version into Bram, Nessa, and
  Pip's election inputs. Calm produces Influential and a seeded `11–9` win.
- All twelve ambient residents now have authored echo styles. A gossip tick
  carrying a new salient Pip account deterministically selects 2–4 co-located
  listeners from authoritative scheduled/event-overridden positions.
- Each selected ambient gets a style-mutated belief version whose parent is
  Pip's exact version, plus a Pip→listener transmission with deterministic
  provider/model provenance. A public `ambient_gossip` event names listeners.
- Ambient NPC state retains at most three recent visible echoes, and holder
  recall is capped to three. Always-visible pair bubbles name the
  Pip→resident route; refresh restores both the chatter and its source.
- Ambient election memory is likewise limited to the last three and attenuated
  by hop distance and carrier style. Skeptical carriers counterweight rather
  than blindly amplify, preserving the seeded `11–9` path.
- Nessa's first principal favor is complete after the storm: accept her dated
  harbor log, deliver it to Elias as evidence, correct Pip's public account,
  and call in Nessa's harbor endorsement. Each step is a consequential,
  validated action with visible dialogue/event/ledger state.
- Delivery derives Reliable and changes Nessa/Elias standing; endorsement
  derives Influential and is stored explicitly on the player. The chain writes
  three Nessa versions plus Elias, Pip, Jonas, and Mae memories, with
  Elias→Pip correction and Nessa→dockworker endorsement transmissions.
- The full normal-play chain declares candidacy and reaches the Landslide
  (`The Town Turns`) ending. Five exact harbor-log belief/version inputs appear
  in the election audit, and refresh preserves favor, correction, endorsement,
  traits, and outcome.
- A declared candidate can give one consequential square speech per day. It
  derives Influential, writes Pip's skeptical firsthand memory, propagates
  proximity echoes, and records the used day so refresh cannot repeat it.
- Declaring without support reaches Humiliation (`No Seconding Voice`); a
  speech-only campaign reaches an audited `10–10` Narrow loss
  (`The Tied Bell`) under Rhea's explicit tie rule.

Validated:

- Ninety-two local API tests pass. Pure election tests cover all six ending
  classes, the 10–10 Rhea tie, deterministic replay IDs, candidacy timing,
  exact promise-version inputs, the 11–9 win, save/restore, content schedule
  shape/reference validation, all-resident phase movement, refresh safety, all
  four Bram effects, playable threat/lie endings, the storm lifecycle,
  all-resident evacuation, awareness, clearing, skipped-interval history, event
  faction damage, all three interventions, their exact vote memories, 2–4
  proximity selection, visible echo restoration, shallow recall, and the
  complete evidence/correction/endorsement chain to Landslide, speech
  once-per-day enforcement, Humiliation, and exact `10–10` Narrow loss.
- Thirteen real Cockroach Cloud tests pass against `hearsay_test`. The election
  test verifies one election row, exactly 20 vote rows, normalized decision
  inputs, Pip's live promise-belief foreign key, and restored final state.
  The schedule test independently recreates the repository, restores every
  resident's afternoon location, and queries the public `schedule_shift` row.
  The threat test queries both belief-backed vote inputs and the public event,
  then recreates the repository and restores the Run out of town result.
  The storm test queries its public event row, recreates the repository, and
  proves weather, active-event state, and all 20 overridden positions survive.
  The argument test additionally proves both directional trust rows reach
  `0.15`, all lifecycle/action events exist, three belief-backed vote inputs
  persist, and repository recreation restores the same election.
  The signature test also proves four hop-two ambient beliefs, four Pip
  transmission edges with `hearsay-ambient-echo-v1`, one public chatter event,
  correct active-memory counts, and unchanged indexed Pip recall.
  The Nessa test proves five holder memories, all three correction/endorsement
  transmission edges, five vote inputs, Nessa's `0.80` trust floor, and
  repository recreation of favor, endorsement, and election state.
  The speech test proves its public event, belief-backed vote inputs, exact
  tie, Rhea winner, Narrow loss ending, and restored election.
- Seven browser playthroughs pass and collectively reach all six endings. The
  first plays arrival → promise → rumor → audited Historian
  fallback → promise kept → candidacy → midnight election. It renders the
  live afternoon movement cue, four labeled Pip→ambient bubbles, Pip's new
  Market row location, storm start, and storm refresh before the `11–9` result and exact v1 promise memory
  explanation. The second threatens
  Bram, shows the two public traits, reaches `0–20` Run out of town, and renders
  the belief-backed threat input in the election explanation.
  The third stages the Day 2 square crowd, calms it, refreshes the active event,
  clears it on Day 3, and renders the exact intervention memory at election.
  The fourth completes Nessa's harbor-log chain, refreshes it, and reaches the
  belief-explained Landslide ending. The expanded layout also fixed an async
  close/reopen race and separates actions, Ledger, and conversation z-layers.
  Two more paths prove unsupported Humiliation and the speech-driven `10–10`
  Narrow loss. Playwright uses three local/two CI workers and a 60-second
  full-story timeout so WebGL overlays remain deterministic.
  The seventh lies about Elias's authority, visibly derives Dishonest, reaches
  Exposed (`The Story Unravels`), and renders the exact lie belief in the audit.
- Ruff, strict mypy, ESLint, strict TypeScript, Vitest, Next.js production
  build, Playwright, asset validation, Cloud/vector doctor, cached BGE probe,
  and real Modal structured-output probe pass.

Remaining:

- Additional principal favors and information/ambition verbs remain.
- Broader multi-hop rumor propagation beyond Pip's immediate ambient listeners.

## Next implementation slice

1. Add Orin's confession favor with reveal/conceal information choices and
   distinct elder-faction trust, memory, and election consequences.
