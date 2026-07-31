# Hearsay — Playable Hackathon Release Plan

**Revised:** 2026-07-30

**Target deadline:** 2026-08-18 at 5:00 PM EDT

**Release principle:** ship a short, attractive, fully playable agent-memory game; do not wait for a full-town art production.

## 1. Goal Contract

Build and deploy a public browser game that a new player can understand and finish in approximately 12–20 minutes.

The release must make three things unmistakable:

1. Greyhaven's featured residents act without waiting for the player, remember different versions of events, and change future behavior because of those memories.
2. CockroachDB is the canonical system of record for game state, agent memory, vector recall, rumor provenance, and final decisions.
3. AWS is part of the running product: Amazon Bedrock Claude powers production interaction and agent language, the application is deployed on AWS, and Amazon S3 stores immutable replay and benchmark artifacts.

This is a scope reduction, not a rewrite. Existing migrations, memory proofs, election logic, tests, content, and completed side stories must be preserved. Out-of-scope systems may remain available in development, but they are not release blockers and should not crowd the default player path.

This plan does **not** by itself authorize cloud provisioning, production deployment, GitHub publication, or Devpost submission. Those actions require the user's approval and credentials. It does authorize local code, documentation, tests, deployment templates, asset integration, and release-profile changes inside this repository.

### North-star demonstration: long-term NPC memory

Hearsay exists to demonstrate that autonomous game agents can have durable,
individual long-term memory, and that CockroachDB makes that memory reliable,
retrievable, revisable, and auditable.

For this project, “long-term memory” means that an NPC memory:

- lives outside the model context and is canonical in CockroachDB;
- survives browser refresh, player absence, API restart, and application
  redeployment;
- remains scoped to the correct run and NPC;
- can be retrieved semantically after other events and conversations occur;
- changes a later autonomous choice, relationship, dialogue, or vote;
- can be contradicted or revised without erasing its earlier versions;
- retains exact source and transmission lineage; and
- can be independently reconstructed through the Managed MCP Historian.

The release-critical proof is:

1. The player makes a promise and confronts Bram.
2. Bram stores a firsthand belief in CockroachDB.
3. Pip autonomously recalls and retells it, creating a new immutable version
   and transmission edge.
4. The player closes or refreshes the game; the API may also be restarted.
5. Pip or Marta later retrieves their own memory through the CockroachDB vector
   index and behaves differently because of it.
6. That remembered consequence affects the final vote.
7. The Town Historian independently traces the decisive memory through the
   Managed MCP Server.

Bedrock Claude is treated as stateless inference. Every production prompt is
rehydrated from CockroachDB memory, and every accepted agent result is written
back with provenance. S3 stores replay evidence only. Neither Bedrock, browser
state, process memory, nor S3 is allowed to become the authoritative NPC memory
layer.

## 2. Source of Truth

1. This plan governs the narrowed 2026 hackathon release scope and milestone order.
2. `docs/Hearsay_Game_Design_Document.md` governs the core fantasy, social-memory design, presentation principles, and player-facing tone.
3. `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs CockroachDB correctness proofs, persistent-memory architecture, Managed MCP, benchmarks, AWS responsibilities, and submission evidence.
4. The current official hackathon rules override all project documents for eligibility and submission compliance.
5. `docs/IMPLEMENTATION_STATUS.md` records what is already working and identifies the next executable slice.

## 3. Verified Hackathon Requirements

Verified against the official Devpost overview and rules on 2026-07-30:

- Build an agentic application that uses CockroachDB as its persistent memory layer.
- Deploy the functional application on AWS.
- Meaningfully integrate at least two listed CockroachDB tools.
- Meaningfully integrate at least one AWS service.
- Provide a public open-source repository with a visible license, dependencies, example configuration, and complete setup/run instructions.
- Provide a functional demo URL.
- Provide a public YouTube or Vimeo demonstration shorter than three minutes that visibly shows the CockroachDB memory layer at work.
- Identify exactly how each claimed CockroachDB tool and AWS service is used.
- Disclose relevant pre-existing work and ensure the submitted work was created during the submission period.
- Keep the demo available through the judging period.

Official references:

- Overview: <https://cockroachdb-ai.devpost.com/>
- Rules: <https://cockroachdb-ai.devpost.com/rules>

### Required sponsor path

Hearsay will use these two CockroachDB tools:

1. **CockroachDB Distributed Vector Indexing** — production NPC recall over holder-scoped active memories.
2. **CockroachDB Cloud Managed MCP Server** — an independently authenticated, read-only Town Historian that reconstructs live rumor lineage and decisive memories.

Hearsay will use these AWS services:

1. **Amazon Bedrock** — Anthropic Claude interaction, dialogue, rumor retelling, and bounded agent decisions through a structured provider contract.
2. **Amazon S3** — immutable redacted replay bundles, benchmark reports, and demo evidence. S3 is not game memory and never replaces CockroachDB.
3. **AWS compute for the public demo** — one small, maintainable application deployment. Prefer the existing native EC2 plan unless a simpler approved AWS runtime is selected during deployment.

## 4. Small Release Scope

### 4.1 Featured cast

The default release presents five featured autonomous residents:

| Resident | Release purpose |
|---|---|
| Marta Vale | Gives the opening promise and demonstrates remembered trust |
| Bram Kett | Creates the confrontation and firsthand account |
| Pip Rook | Mutates and carries the signature rumor |
| Talia Fen | Provides the optional privacy-versus-influence dilemma and uses the complete production sprite pack |
| Rhea Morn | Converts the town's memories into the final election consequence |

The player is the Newcomer.

Existing Elias, Orin, Nessa, and ambient-resident systems remain in the repository. They may appear as background tokens, witnesses, or optional development content, but they do not require new animation packs and are not part of the release-critical path.

### 4.2 Play space

Use a compact release map centered on:

- The Gull & Anchor
- Market Row
- Town Square and notice board
- Midwife's Cottage
- Guildhouse

The existing twelve-location graph may remain authoritative internally. The release UI should emphasize only the locations needed by the featured story and avoid presenting unused waypoints as obligations.

#### Approved visual-map amendment — 2026-07-31

The focused release now presents the complete twelve-location graph as one
continuous, bright 30×18-tile exterior village. All landmarks are visible,
reachable, and respond to nearby interaction, but optional exploration never
spends or replaces one of the ten guided story actions. The five featured story
residents remain the only mandatory route; Nessa, Elias, and Orin provide short
focused-profile conversations without exposing their longer full-profile favor
trees.

The Town Square is the navigation hub. Stone marks civic routes, warm dirt
connects residential and market districts, wood marks the northwest harbor,
and dense edge scenery conceals the world boundary. A gold in-world marker,
compact objective card, signposts, plaques, minimap, and contextual bottom
prompt provide direction without turning the full location set into twelve
simultaneous objectives.

### 4.3 Playable story

The default run is one compressed election arc:

1. Arrive in Greyhaven and meet Marta.
2. Promise to help with the blocked shipment, or refuse.
3. Confront Bram by threatening, flattering, negotiating, or lying.
4. The autonomous town tick runs. Pip hears and retells a changed version.
5. Talk to a resident after the tick and see recalled memory alter tone and available choices.
6. Resolve or break Marta's promise.
7. Optionally handle Talia's sick-house request privately or turn it into public warning.
8. Make one final public/election choice.
9. Finish with an explainable vote and one of three headline outcomes:
   - trusted win;
   - narrow loss;
   - public disgrace/exposure.
10. Open the Town Historian to trace the decisive rumor from source to outcome.

Existing additional endings may still be selected by the authoritative classifier, but the release only promises and rehearses these three outcome families.

### 4.4 Time and action budget

- Target 12–20 minutes for a first run.
- Use at most 10 consequential player actions in the critical path.
- Movement, observation, reading, and opening the Historian remain free.
- Run an autonomous town tick after every two consequential player actions and at authored story boundaries.
- Avoid a tutorial wall. The opening promise and first visible gossip hop teach the game.

## 5. Autonomous Agent Contract

The agents must look alive, but their autonomy must remain bounded, auditable, and affordable.

For each autonomous tick, every eligible featured agent follows:

```text
PERCEIVE
  current location + nearby agents + active event + relationship state
        |
RECALL
  holder-scoped vector search in CockroachDB, then relational reranking
        |
DECIDE
  choose one allowed action from structured Bedrock Claude output
        |
VALIDATE
  reject unknown targets/actions and fall back deterministically if needed
        |
ACT
  move, speak, share a rumor, react, or wait
        |
COMMIT
  action + immutable memory version + transmission + active projection
  + relationship consequence in one bounded serializable transaction
        |
RENDER
  movement, paired speech bubble, memory cue, and activity-feed entry
```

### Allowed release actions

- Move to an adjacent authored location.
- Talk to a co-located resident.
- Share one salient public rumor.
- React to a remembered promise or contradiction.
- Wait.

Agents cannot invent game entities, directly change votes, write arbitrary database state, or perform external tool calls. The model proposes language and a bounded intent; deterministic code owns validation and game consequences.

### Visible autonomy requirements

After each autonomous tick the player must be able to see at least two of:

- an NPC moving between waypoints;
- a named speaker → listener bubble;
- a changed rumor sentence;
- a short “Town activity” entry;
- a memory-conditioned greeting or relationship cue;
- the Historian lineage gaining a new hop.

Do not add an opaque multi-agent framework merely to claim autonomy. The existing service, scheduler, provider interface, and CockroachDB transaction boundary are the agent runtime.

## 6. CockroachDB Memory Contract

CockroachDB remains the only canonical operational store.

If CockroachDB is unavailable, the deployed game must fail visibly or enter an
explicitly labeled read-only/degraded state. It must never fabricate continuity
from browser state, an LLM transcript, a process cache, or an S3 replay. Removing
CockroachDB must remove the agents' ability to remember and explain prior
events; that dependency is intentional and central to the submission.

Required persisted state includes:

- runs, players, agents, locations, schedules, actions, and events;
- conversations and structured claims;
- propositions, holder-specific beliefs, and immutable belief versions;
- active memories with `VECTOR(384)` embeddings;
- rumor transmissions with exact parent and child versions;
- relationships, promises, public traits, and election inputs;
- retrieval traces, model provenance, retries, latency, and fallback status;
- final votes and the exact memories that influenced them;
- S3 artifact keys, hashes, and version metadata, but not the artifact as canonical game state.

### Production recall

1. Constrain by run, holder, and active status.
2. Use the CockroachDB distributed vector index to retrieve semantic candidates.
3. Rerank with confidence, salience, recency, relationship, and source trust.
4. Pass only a small validated set to Bedrock.
5. Record the candidates and selections in a retrieval trace.
6. Display a concise memory cue in the conversation UI.

Every memory-conditioned interaction must expose enough evidence for the player
or judge to verify that recall was real: holder, memory summary, belief/version
reference, retrieval reason, and visible behavioral consequence. Raw embeddings
and internal prompts remain hidden.

### Transaction boundary

Model inference and embedding work occurs outside database transactions. Validated outcomes are committed using bounded serializable retries. A gossip action must atomically persist its event, source version, child version, transmission edge, active-memory update, relationship effect, and model provenance.

## 7. Amazon Bedrock Claude Contract

Add a production `BedrockInferenceProvider` behind the existing inference interface.

Use the Bedrock Converse API with a configured Anthropic Claude model or inference profile. The model identifier must be configuration, not hard-coded, because regional availability and model access can change.

Bedrock is load-bearing for:

- player-to-NPC dialogue grounded in recalled memory;
- concise rumor retelling that preserves the underlying proposition;
- contradiction classification/explanation within a closed schema;
- selecting one action from the release allowlist for autonomous ticks.

Every response must:

- validate against a strict Pydantic schema;
- record provider, model/inference profile, operation, latency, token usage when available, attempts, and fallback status;
- exclude secrets and raw credentials from logs or rows;
- time out and fall back without corrupting state;
- never be called from inside a CockroachDB transaction.

For local/offline tests, retain the deterministic provider. Modal may remain as a development adapter, but the deployed demo and recorded submission path must visibly use Bedrock.

## 8. Amazon S3 Contract

Use a private, versioned bucket with least-privilege access from the AWS application role.

At game completion, generate a redacted replay bundle containing:

- run seed and release-profile version;
- ordered public actions and autonomous ticks;
- rumor lineage IDs and mutation summaries;
- final result and decisive memory references;
- provider/model/fallback provenance;
- no database credentials, service keys, private prompts, or unrelated player data.

Upload the JSON bundle to an immutable run-specific key. Store the bucket-independent object key, content SHA-256, ETag/version ID when available, size, and creation time in CockroachDB. The game may provide a short-lived presigned download URL.

Also upload frozen benchmark reports and demo-proof manifests. CockroachDB remains the live memory system; S3 is evidence and replay storage only.

## 9. Presentation and Asset Plan

The release uses a deliberate illustrated-board aesthetic rather than pretending to be a fully commissioned town.

- Use the accepted Newcomer sprite pack for the player.
- Integrate the complete Talia production pack for visible idle/walk/talk states.
- Represent other featured residents with consistent colored tokens, role symbols, names, and strong dialogue cards.
- Static portrait crops may be used only when their backgrounds and licenses are acceptable. Elias and Orin concept sheets are not required.
- Preserve the existing CSS/SVG waypoint town, then improve hierarchy, lighting, weather treatment, movement tweening, bubbles, and selection states.
- Do not build new tilesets, interiors, cutscenes, lip sync, or bespoke animation packs.
- Do not let missing character art block playability, memory proof, AWS integration, or submission.

## 10. Architecture

```text
Browser
  Next.js game UI
  - compact town board
  - dialogue and memory cues
  - autonomous activity feed
  - election result and Historian
          |
          | HTTPS REST
          v
AWS application runtime
  FastAPI authoritative game service
  - action validation
  - autonomous tick scheduler
  - Bedrock Claude provider
  - S3 replay exporter
          |
          +-----------------------> Amazon Bedrock
          |                         structured language and bounded decisions
          |
          +-----------------------> Amazon S3
          |                         replay and benchmark evidence
          |
          v
CockroachDB Cloud
  - canonical world state
  - immutable agent memories and lineage
  - distributed vector recall
  - model/retrieval/audit traces
          |
          v
CockroachDB Cloud Managed MCP Server
  read-only Town Historian over live state
```

The browser never receives CockroachDB, MCP, Bedrock, or S3 credentials.

## 11. Implementation Milestones

### Milestone A — Scope lock and release profile

- Add a `hackathon_small` release profile without deleting full-scope content.
- Select five featured agents and the compact location set.
- Limit the default critical path and action budget.
- Hide unfinished or distracting actions from the default UI.
- Update onboarding and test fixtures for the short run.

**Gate:** a new run reaches an ending in 12–20 minutes without developer controls.

### Milestone B — Playability and visible autonomy

- Integrate Talia's runtime sprite exports.
- Improve town-board visual hierarchy and movement feedback.
- Add a compact autonomous-activity feed and named gossip bubbles.
- Make memory-conditioned greetings, tone, and choices immediately visible.
- Ensure every two player actions produce an understandable autonomous tick.

**Gate:** a player can point to who moved, who spoke, what changed, and what an NPC remembered.

### Milestone C — Bedrock Claude production path

- Implement and test the Bedrock provider.
- Use one configured Claude model/inference profile for the five featured agents.
- Add structured autonomous-action selection.
- Record truthful model provenance and cost/latency fields.
- Keep deterministic fallbacks for failure safety, clearly labeled in proof views.

**Gate:** a real configured Bedrock request drives dialogue and one autonomous rumor retelling, while malformed and unavailable responses fail safely.

### Milestone D — CockroachDB sponsor proof

- Keep distributed vector retrieval in the production dialogue path.
- Capture `EXPLAIN` evidence for the prefixed vector index.
- Finish an independently authenticated, read-only Managed MCP Historian success over live run state.
- Preserve the concurrent-conflict and immutable-lineage tests.
- Make the Historian reconstruct the rumor that affected the final result.
- Prove the same NPC memory survives browser refresh, API restart, and
  repository/service recreation, then changes a later autonomous action or
  vote.
- Demonstrate that Bedrock receives selected CockroachDB memory references
  rather than relying on an accumulated model transcript.

**Gate:** the deployed proof shows durable long-term NPC memory changing
behavior after a restart, and both required CockroachDB tools doing load-bearing
work; direct database fallback is visibly marked `not MCP proof`.

### Milestone E — S3 evidence and AWS deployment

- Implement redacted replay-bundle generation and checksum validation.
- Upload replay and benchmark artifacts to a private versioned S3 bucket.
- Persist object metadata in CockroachDB and expose a short-lived download action.
- Finalize the least-privilege IAM policy and native AWS application deployment.
- Deploy the functional demo on AWS with health checks and restart behavior.

**Gate:** a judge can finish a run, refresh it from CockroachDB, download its S3 replay evidence, and continue using the public AWS URL.

### Milestone F — Submission and rehearsal

- Run local, Cockroach Cloud, Bedrock, S3, production-build, and browser tests.
- Perform three clean-browser judge-path rehearsals.
- Update README setup, architecture, tool-usage, AWS-usage, security, disclosure, and fallback sections.
- Produce the architecture diagram.
- Record a public video under three minutes showing:
  1. player action;
  2. autonomous rumor hop;
  3. memory-conditioned response;
  4. CockroachDB vector/MCP proof;
  5. Bedrock provenance;
  6. S3 replay evidence;
  7. final consequence.
- Submit early and keep the demo healthy through judging.

**Gate:** every service and tool claimed on Devpost is visible in the running product or its recorded proof.

## 12. Quality Gates

- Frontend typecheck, lint, unit tests, production build, and critical Playwright paths pass.
- API unit tests and isolated Cockroach Cloud integration tests pass.
- Bedrock contract tests cover schema validation, timeout, throttling, invalid output, and deterministic fallback.
- S3 tests cover redaction, checksum, idempotent keying, version metadata, least-privilege failure, and presigned-download expiry.
- Refresh restores the same world, memories, relationships, and election state.
- API restart and application redeployment restore the same run from
  CockroachDB without replaying a model transcript.
- Autonomous ticks are idempotent and cannot double-apply on retry.
- No orphan belief version, missing transmission parent, stale active-memory pointer, or unexplained decisive vote is allowed.
- A model or network failure never silently changes authoritative state.
- Secrets never reach browser bundles, replay files, logs, test output, or documentation.

## 13. Definition of Done

The release is done when:

- a judge can open the public AWS URL and finish a coherent game without instructions from the developer;
- the default run spotlights five memorable residents and requires no new character asset packs;
- autonomous agents visibly move, talk, share a changed rumor, and react to stored memory;
- CockroachDB persists and retrieves the long-term NPC memory that survives a
  restart and changes a later interaction, autonomous decision, and final vote;
- Distributed Vector Indexing is used in the production recall path;
- the Managed MCP Historian independently reconstructs live lineage;
- Bedrock Claude is visibly and truthfully used in the deployed interaction path;
- S3 contains a validated replay/benchmark artifact whose metadata is linked from CockroachDB;
- the optimized build, automated tests, clean-browser rehearsal, README, public repository, demo URL, and under-three-minute video are ready;
- no out-of-scope art, event, side quest, or full-town feature remains a release blocker.

## 14. Explicit Non-Goals

- New animated packs for every NPC.
- A bespoke full-town tileset.
- More than five release-critical residents.
- More than the compact critical path and three outcome families.
- Festival Night or additional event-deck content.
- Second favors or a broad verb sandbox.
- Multiplayer.
- Interiors as separate scenes.
- Bedrock Agents, Lambda, EKS, SageMaker, or other services that are not actually needed.
- Moving operational memory or vector search out of CockroachDB.
