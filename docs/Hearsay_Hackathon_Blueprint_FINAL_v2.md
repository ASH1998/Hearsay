# Hearsay
## A Social Mystery Game Where Every Rumor Has a Traceable History

> **One-line pitch:** A persistent AI mystery game where NPCs gossip when you are not around, every character remembers a different version of events, and solving the case means shaping what the town believes—not merely discovering the truth.

> **Tagline:** The truth is what survives the telling.


## Final Infrastructure Clarification

- **CockroachDB Cloud:** Hosted CockroachDB instance and complete persistent-memory layer.
- **Amazon Bedrock:** LLM inference only.
- **Local embedding model:** Generates memory and query embeddings on the application host, or on Modal GPU compute if acceleration is needed.
- **Amazon S3:** Stores benchmark reports, replay bundles, seeds, exported graphs, and submission artifacts.
- **Application hosting:** Amazon EC2 or another suitable general-purpose host runs the frontend, API, deterministic game logic, scheduler, and default embedding service.
- **Modal:** Optional GPU compute for the local embedding model or other genuinely GPU-intensive auxiliary workloads.
- **Not claimed unless actually implemented:** AWS Lambda, ECS, EventBridge, CloudWatch, SageMaker, or Bedrock embedding models.


---

## Document Status

- **Project:** Hearsay
- **Alternate titles:** The Town That Remembers, Commonplace, Everwake
- **Competition:** CockroachDB × AWS Hackathon — Build with Agentic Memory
- **Deadline:** August 18, 2026
- **Builder:** Solo technical founder/engineer
- **Build window:** Approximately 4.5 weeks
- **Primary form:** Persistent social-mystery game
- **Core sponsor thesis:** Persistent AI game worlds need a shared, distributed, transactional memory substrate where semantic recall, social relationships, quest state, and belief provenance remain coherent across agents, sessions, and eventually players.
- **Scope principle:** One polished mystery, eight excellent characters, one unforgettable rumor mechanic, one honest benchmark.
- **Deployment summary:** CockroachDB Cloud hosts the memory database; Bedrock supplies LLM inference only; a local embedding model generates vectors on the application host or optional Modal GPU compute; S3 stores artifacts; EC2 or another host runs the application.

---

# 1. Submission Requirements and Deliverables

The final Devpost submission must explicitly satisfy the following requirements.

## 1.1 Public demo video

- Include a video **under three minutes**.
- Upload it to **YouTube or Vimeo**.
- Set the video to **public**.
- The video must visibly demonstrate:
  - The playable Hearsay experience
  - The CockroachDB memory layer at work
  - A rumor spreading and mutating
  - Character recall powered by Distributed Vector Indexing
  - The Managed MCP Historian reconstructing rumor lineage
  - A real concurrent belief update or transactional consistency proof
  - A gameplay consequence caused by the town's remembered beliefs

Use real captured behavior. Do not rely on fake transaction output, mocked tool calls, or simulated sponsor integrations.

## 1.2 CockroachDB tool disclosure

The submission must identify every CockroachDB tool used and explain what the application or agent actually did with it.

| CockroachDB tool | Exact role in Hearsay | Visible proof |
|---|---|---|
| **CockroachDB Cloud Managed MCP Server** | Powers the independent, read-only Town Historian. The Historian queries live beliefs, transmissions, decisions, and schema state to answer questions such as “Who first accused Bram?” and “Which memories caused the final arrest?” | Live Historian query in the video with reconstructed source rows and rumor path |
| **Distributed Vector Indexing** | Retrieves semantically relevant active beliefs for each NPC, scoped by character and status before relational reranking by confidence, trust, salience, and quest relevance | Real dialogue recall plus query and `EXPLAIN` evidence |
| **ccloud CLI** | Provisions or inspects the CockroachDB Cloud environment, captures machine-readable cluster configuration, and produces readiness evidence for the repository and replay bundle | CLI output or JSON artifacts linked from the README |
| **CockroachDB Agent Skills** | Optional implementation and readiness support for schema validation, retry guidance, transaction patterns, and deployment checks | Readiness report or clearly documented skill usage |

For each tool, the submission must state:

1. Which component invoked it
2. What data it read or wrote
3. What game or technical outcome depended on it
4. Where judges can see proof that the integration was real

Avoid vague statements such as “we used MCP” or “we used vector search.”

## 1.3 AWS service disclosure

### Deployment clarification

- **CockroachDB Cloud** provides the hosted CockroachDB instance and the complete persistent-memory layer.
- **Amazon Bedrock** is used only for LLM inference.
- **A local embedding model** generates vectors for character memory retrieval.
- The embedding model runs on the application host by default, or on **Modal GPU compute** only if acceleration is genuinely needed.
- **Amazon S3** is used only for benchmark reports, replay bundles, seeds, exported graphs, and submission artifacts.
- **Amazon EC2 or another general-purpose host** runs the game API, frontend, scheduler, deterministic game logic, and local embedding service.
- The submission must not imply that Bedrock hosts the application.
- The project must not claim Lambda, ECS, EventBridge, CloudWatch, or any other AWS service unless it is actually implemented.


The submission must identify every AWS service used and explain its concrete role.

| AWS service | Exact role in Hearsay | Visible proof |
|---|---|---|
| **Amazon Bedrock** | Provides character dialogue, structured proposition extraction, controlled rumor retelling, and contradiction analysis | Model IDs, structured outputs, and live dialogue behavior |
| **Amazon S3** | Stores frozen benchmark reports, replay bundles, scenario seeds, exported rumor graphs, and submission evidence | S3 artifact references or links in the README and submission |

Embedding generation is **not** provided by AWS. Hearsay uses a local embedding model hosted with the application or on optional Modal GPU compute.

Only these AWS services are part of the committed architecture.

The application itself may run on Amazon EC2 or another suitable host. EC2 should be listed as an application-hosting choice only if it is actually used in the final build. Modal may be listed separately as an optional external GPU-compute provider if it is genuinely used.

The project does **not** claim AWS Lambda, ECS, EventBridge, CloudWatch, or other AWS services unless they are actually implemented.


## 1.4 Architecture diagram

An architectural diagram is optional under the rules, but Hearsay should include one.

It should show:

```text
Player Browser
    ↓
Frontend + Game API
(hosted on EC2 or another suitable application host)
    ├── Game rules and deterministic state transitions
    ├── Gossip scheduler and background jobs
    ├── CockroachDB transactions
    ├── Bedrock orchestration
    └── S3 artifact export
         │
         ├──────────────► Amazon Bedrock
         │                  ├── Character dialogue
         │                  ├── Proposition extraction
         │                  ├── Rumor mutation
         │                  └── Contradiction analysis
         │
         ├──────────────► Local Embedding Model
         │                  └── Memory embeddings
         │
         ├──────────────► CockroachDB Cloud
         │                  ├── Propositions
         │                  ├── Beliefs
         │                  ├── Belief versions
         │                  ├── Transmissions
         │                  ├── Relationships
         │                  ├── Decisions
         │                  └── Distributed Vector Index
         │
         └──────────────► Amazon S3
                            ├── Benchmark reports
                            ├── Replay bundles
                            ├── Scenario seeds
                            ├── Exported rumor graphs
                            └── Submission artifacts

Town Historian
    ↓
CockroachDB Cloud Managed MCP Server
    ↓
Read-only queries against CockroachDB Cloud

Optional Modal GPU Worker
    └── Used only to accelerate the local embedding model or other
        genuinely GPU-intensive auxiliary work
```

The diagram should emphasize:

- CockroachDB Cloud is the hosted database instance and canonical memory layer
- Bedrock performs LLM inference only
- A local embedding model generates all memory vectors
- S3 stores reproducibility evidence and exported artifacts only
- EC2 or another application host runs the frontend, API, scheduler, deterministic game logic, and default embedding service
- Modal is optional and used only to accelerate embeddings or other real GPU-heavy auxiliary workloads
- The Historian independently audits CockroachDB through the Managed MCP Server

## 1.5 CockroachDB feedback

Feedback is optional, but a concise implementation-grounded section should be included.

Capture feedback on:

- Managed MCP setup and authentication
- Discoverability of MCP tools
- Read-only permission clarity
- Vector-index setup and `EXPLAIN` visibility
- Prefix-filtered vector retrieval ergonomics
- Transaction retry guidance for agent workloads
- ccloud JSON consistency
- Agent Skills usefulness
- Missing capabilities for persistent AI-game workloads

Suggested format:

| Area | What worked | Friction | Suggested improvement |
|---|---|---|---|
| Managed MCP | Read-only auditing was easy to reason about | Tool naming or auth setup required extra discovery | Add a game-memory lineage example |
| Vector indexing | Kept semantic and relational state together | Verifying index usage required manual `EXPLAIN` work | Add diagnostics for hybrid reranking queries |
| Transaction retries | Serializable correctness fit belief updates | Agent-oriented retry examples were limited | Publish a canonical retry-wrapper pattern |

Feedback must be based on actual implementation experience, not invented criticism.

## 1.6 Required submission package

The final package must contain:

- Public GitHub repository
- Open-source license
- Live playable demo
- Public YouTube or Vimeo video under three minutes
- Written explanation of CockroachDB tool usage
- Written explanation of AWS service usage
- Architecture diagram
- Reproducible benchmark
- CockroachDB feedback section
- Setup and reproduction instructions
- Real frozen metrics with no fabricated results

---

# 2. Executive Summary

Hearsay is a social mystery game set in a small harbor town whose characters gossip, remember, misinterpret, accuse, forgive, and carry grudges.

The player arrives shortly before a royal inspector is due to judge a serious crime: a sacred relic has vanished from the town chapel. Eight townspeople each know only part of the truth. Some are honest, some mistaken, one is deliberately lying, and several have reasons to distrust one another.

The player has a limited number of conversations before nightfall. They can:

- Question characters
- Reveal or conceal evidence
- Tell the truth
- Lie
- Plant a rumor
- Correct a rumor
- Build trust
- Accuse a suspect
- Convince one character to confront another

After every few player actions, the town advances. Characters meet, exchange salient beliefs, and pass stories onward. Each retelling may drift.

A statement such as:

> “The harbormaster buried a silver key beneath the bell.”

may become:

> “The harbormaster hid a treasury key.”

and later:

> “The harbormaster stole the chapel key.”

Every retelling creates a new, provenance-linked belief. Characters do not share one global memory. Each holds their own version of a proposition, confidence level, trust context, and source history.

The player wins only if they influence the town’s final belief state strongly enough for the constable and inspector to reach the correct conclusion.

The game is powered by CockroachDB:

- **Distributed Vector Indexing** retrieves semantically relevant memories for each character.
- **Serializable transactions** keep concurrent updates to shared belief state coherent.
- **Relational provenance** records who told whom, what changed, and which belief version influenced each decision.
- **The CockroachDB Cloud Managed MCP Server** powers a read-only Town Historian who reconstructs any rumor’s complete family tree.
- **Amazon Bedrock** powers character dialogue, structured claim extraction, contradiction analysis, and controlled rumor mutation.
- **Amazon S3** stores benchmark reports, replay bundles, and exported evidence.

The flagship demo is simple:

1. The player tells the innkeeper a secret.
2. The secret spreads through the town and mutates.
3. The constable later confronts the player using the distorted rumor.
4. Two conflicting updates reach the constable concurrently.
5. CockroachDB preserves both histories while keeping one coherent active belief.
6. The Historian reconstructs the entire chain through the official Managed MCP Server.
7. The player uses evidence to reshape the town’s belief and solve the case.

The product is not “a chatbot village.”

It is:

> **A game where information is the weapon, memory is the world state, and reputation is the consequence.**

---

# 3. Winning Thesis

Most agent-memory projects demonstrate one of the following:

- An assistant remembers a user
- An agent resumes after failure
- A vector store retrieves prior text
- A dashboard displays stored memories
- A workflow uses past decisions

Hearsay demonstrates a different and more ambitious memory model:

> **Memory is social, contested, versioned, consequential, and shared across autonomous characters.**

The player does not merely retrieve information from NPCs. They alter:

- What characters believe
- Who trusts whom
- Which version of an event dominates
- Which dialogue options become available
- Which suspect is accused
- How the town remembers the player

This creates a game mechanic that cannot exist without durable agent memory.

## 3.1 What judges should remember

Primary memory hook:

> “That was the game where I told the innkeeper something, and the constable confronted me with a twisted version of it.”

Technical memory hook:

> “Every rumor had a complete transaction-backed family tree.”

Sponsor memory hook:

> “They showed a real use case for CockroachDB in persistent AI game worlds.”

## 3.2 Strategic position

Hearsay deliberately avoids crowded hackathon categories:

- SRE and incident-response agents
- Generic personal memory
- Coding-assistant memory
- Finance copilots
- Memory SDKs
- RAG dashboards
- Generic chat interfaces

It competes in an underexplored category:

> **Persistent AI games and social simulations whose world state is composed of agent beliefs.**

---

# 4. Product Positioning

## 4.1 Player-facing pitch

> You have one day to solve a crime in a town where everyone talks. Discover secrets, decide whom to trust, plant or correct rumors, and shape what the town believes before the inspector arrives.

## 4.2 Judge-facing pitch

> Hearsay is a social mystery game where NPC memories form a shared but contested belief network. Every retelling creates a versioned belief with provenance, and every important decision can be traced back to the conversations that caused it.

## 4.3 CockroachDB-facing use case

> Hearsay is a reference architecture for persistent AI NPCs in online games: semantic memory, social relationships, quest state, reputation, shared world canon, and concurrent player influence stored coherently in one distributed transactional system.

## 4.4 Potential industry applications

- Persistent role-playing games
- MMORPG NPC memory
- Social simulation games
- Live-service narrative games
- Multiplayer mystery games
- AI companions
- Procedural storytelling systems
- Faction and reputation systems
- Player-generated narrative worlds

---

# 5. The Game

## 5.1 Setting

A compact harbor town called **Greyhaven**.

| Character | Role | Social function |
|---|---|---|
| Marta Vale | Innkeeper | Hears everything; trusted by travelers |
| Elias Ward | Constable | Makes the final arrest |
| Father Orin | Priest | Holds confessions; high trust, low openness |
| Nessa Reed | Fisher | Knows harbor movements |
| Bram Coyle | Merchant | Influential, self-interested, manipulative |
| Talia Fen | Midwife | Trusted across factions |
| Pip Marr | Town gossip | Fast transmission, low reliability |
| The Historian | Archivist | Read-only forensic interface via Managed MCP |

The world uses stylized portraits, dialogue, a compact town map, and a visible clock. No 3D engine is required.

## 5.2 The flagship mystery: The Chapel Relic

A ceremonial relic disappeared from the chapel the previous night. The royal inspector arrives at midnight. The player has twelve meaningful actions before the inspector demands an answer.

### Ground truth

- Bram arranged the theft.
- Nessa unknowingly transported a locked crate.
- Father Orin heard a partial confession.
- Pip saw someone near the chapel but misidentified them.
- Marta knows Bram paid for a private room.
- Elias initially trusts Bram more than the player.
- Talia possesses physical evidence that contradicts the dominant rumor.

### Player objective

Cause the constable and inspector to identify the real culprit while preserving enough personal credibility to avoid becoming a suspect.

### Win conditions

The player wins if:

- The correct culprit is accused
- At least two credible supporting beliefs exist
- The constable’s final confidence exceeds the decision threshold
- The player’s reputation remains above the minimum threshold

### Loss conditions

The player loses if:

- An innocent person is arrested
- The culprit escapes
- The player becomes the dominant suspect
- The player’s evidence is rejected because their credibility collapses
- The inspector reaches midnight without a coherent case

---

## 5.3 Instancing model (decided, not deferred)

**Each visitor plays a private instance of the mystery. One thin shared layer persists across all instances.**

- **Per-player instance:** ground truth, beliefs, transmissions, clock, and endings are scoped to the visitor. Judge #2 never inherits judge #1's solved case or wreckage. Demo reliability is absolute.
- **The Town Ledger (shared, thin):** a single cross-instance table of visitor-level outcomes — who visited, whether they lied, who they accused, whether an innocent was jailed, final credibility. The Historian can query it live: *"Four visitors have accused Bram. Two lied to Marta. One got Nessa wrongly arrested."*
- **Why both:** instancing protects the game; the Ledger preserves the participatory identity — the town genuinely remembers *every judge who has ever played*, and says so.
- **Return sessions:** a returning visitor's new instance is seeded from their Ledger entry ("The last time you visited Greyhaven, an innocent man spent a night in jail because of your story.").
- If late: the Ledger degrades to a read-only epilogue stat, never cut entirely — it is one table and one Historian query.

---

# 6. Core Game Loop

```text
Investigate
    ↓
Learn a fact or rumor
    ↓
Choose what to reveal, conceal, distort, or correct
    ↓
NPC records a belief about the event and the player
    ↓
Town clock advances
    ↓
NPCs exchange salient beliefs
    ↓
Rumors mutate, branch, conflict, or gain corroboration
    ↓
Relationships and available dialogue change
    ↓
Player investigates again
    ↓
Final accusation is produced from the town's belief state
```

## 6.1 Player actions

Each action consumes time:

- Ask a direct question
- Present evidence
- Reveal another character’s statement
- Tell a lie
- Correct an existing rumor
- Ask a character to speak to someone
- Spend social capital
- Make a formal accusation

## 6.2 Gossip ticks

A gossip tick occurs after every two player actions.

Additionally, **idle drift ticks** run on a slow wall-clock schedule (e.g., every 2–4 hours) for any instance with unfinished business: paused mysteries, contested rumors, or a returned player's pending consequences. Drift ticks are capped (1–2 hops, economy model only) so cost stays near zero, but they make the pitch line literally true: the town keeps talking when you are not around, and a player who returns the next day finds the rumor has traveled.

The game selects a small number of character pairs using:

- Relationship affinity
- Physical or social proximity
- Belief salience
- Whether the listener already knows the proposition
- Whether the speaker has a reason to disclose it
- Cost and rate limits

Each hop:

1. Reads the speaker’s current belief version.
2. Produces a controlled retelling.
3. Writes the listener’s new or updated belief.
4. Records a transmission edge.
5. Updates trust and affinity where appropriate.
6. Unlocks consequences or dialogue if thresholds are crossed.

## 6.3 The player’s real resource

The player is not mainly managing health, money, or combat power. They are managing:

- Credibility
- Access
- Information
- Timing
- Source reliability
- Rumor reach
- Social trust

---

# 7. Why Memory Is Gameplay

A conventional NPC memory feature produces moments such as:

> “I remember that you like apples.”

Hearsay produces consequences:

> “You accused my brother of theft. I told the constable. Until you clear his name, you are not entering the docks.”

Memory affects:

- Reputation
- Access to locations
- Character cooperation
- Evidence credibility
- Quest branches
- Accusations
- Endings
- Future sessions

## 7.1 Example rumor chain

```text
Player:
“I saw the harbormaster bury a silver key.”

Marta:
“The harbormaster buried a silver key.”

Bram:
“The harbormaster hid a treasury key.”

Pip:
“The harbormaster stole the chapel key.”

Elias:
“The harbormaster may be responsible for the relic theft.”
```

The game preserves:

- Original wording
- Each mutation
- Each holder
- Every source
- Trust at transmission time
- Confidence changes
- The exact final decision influenced by the rumor

## 7.2 Persistent consequences

On return, the town may remember:

- Whether the player lied
- Which faction they helped
- Which person was wrongly accused
- Whether an earlier claim was later disproven
- Whether the player normally provides reliable information
- Which NPCs resent or trust them

A future scenario can begin with:

> “The last time you visited Greyhaven, an innocent man spent a night in jail because of your story.”

---

# 8. Agentic Memory Model

Hearsay separates facts, beliefs, versions, and transmissions.

## 8.1 Proposition

A normalized question or claim about the world.

Examples:

- Who stole the chapel relic?
- Did Nessa’s boat arrive before midnight?
- Was Bram present at the chapel?
- Is the player a reliable source?

A proposition may have multiple competing positions.

## 8.2 Belief

A particular character’s stance on a proposition.

Examples:

- Marta believes Bram was involved.
- Elias believes Nessa is the primary suspect.
- Pip believes the player is hiding something.

Different characters may hold conflicting beliefs simultaneously.

## 8.3 Belief version

A character’s belief may change over time.

```text
Elias belief v1:
“Nessa is probably responsible.”

Elias belief v2:
“Nessa transported the crate but may not have known what it contained.”

Elias belief v3:
“Bram arranged the theft and used Nessa’s boat.”
```

Versions are immutable. A new version supersedes the previous active version.

## 8.4 Transmission

A transmission records how one belief version produced another character’s belief version.

```text
Marta belief v2
    ↓ told Elias during gossip tick 14
Elias belief v1
```

A transmission contains:

- Speaker
- Listener
- Parent belief version
- Resulting belief version
- Original and retold text
- Mutation summary
- Trust at transmission time
- Tick identifier
- Model identifier
- Timestamp

## 8.5 Evidence

Evidence is distinct from hearsay.

Examples:

- Signed harbor ledger
- Torn chapel cloth
- Ship arrival record
- Room payment receipt
- Witness statement

Evidence can support or contradict propositions and changes how characters evaluate rumors.

## 8.6 Social memory

Relationships store:

- Trust
- Affinity
- Fear
- Debt
- Last interaction
- Faction alignment
- Player credibility

These values influence:

- Whether information is disclosed
- How strongly a report is believed
- Whether a character will repeat it
- Which dialogue options appear

---

# 9. Canon, History, and Belief

The project must not claim that every statement becomes accepted truth.

It distinguishes four layers:

| Layer | Meaning |
|---|---|
| Record | Something was said or observed |
| Rumor | The record was transmitted socially |
| Belief | A character currently accepts a version |
| Canon | The game’s authored or proven ground truth |

Everything meaningful becomes part of **history**. Not everything becomes accepted belief. Not every belief becomes canon.

This lets the game preserve lies without treating them as truth.

---

# 10. Conflict and Deception

## 10.1 Conflicting beliefs

When a character receives a claim that conflicts with their active belief:

1. The incoming claim is stored with provenance.
2. The current active belief is not silently overwritten.
3. The game compares source trust, evidence support, corroboration, recency, and character biases.
4. The character may accept the new claim, reduce confidence, mark the proposition contested, reject it, or ask for more evidence.
5. Both histories remain queryable.

## 10.2 Player deception

Lying is allowed gameplay.

A lie may succeed if:

- The player is trusted
- The target lacks conflicting evidence
- The claim matches existing bias
- The rumor reaches influential characters
- The lie is repeated by independent sources

A lie may fail if:

- Provenance points back to the player
- Stronger evidence appears
- Trusted characters contradict it
- The player’s prior claims were unreliable

## 10.3 Consequences of getting caught

- Reputation loss
- Locked dialogue
- Higher evidence threshold
- NPC hostility
- New accusation branches
- Alternate ending
- Future-session memory

---

# 11. CockroachDB Integration

The project uses at least two required CockroachDB tools in load-bearing roles.

## 11.1 Distributed Vector Indexing

Used for character memory recall.

When generating dialogue, the application first creates a query embedding using the local embedding model, then retrieves memories semantically related to:

- The current question
- Mentioned people
- Active quest propositions
- Current location
- Player identity

Retrieval is scoped by exact character and status prefixes before relational reranking.

The system retrieves vector candidates first and then reranks them using:

- Semantic similarity
- Salience
- Confidence
- Source trust
- Quest relevance
- Recency

Vector search and relational state remain in one database.

## 11.2 CockroachDB Cloud Managed MCP Server

The Town Historian is an independent read-only forensic agent.

Players and judges can ask:

- Who first claimed Bram was at the chapel?
- How did the silver-key story change?
- Which beliefs caused Elias to accuse Nessa?
- Who currently believes the player?
- Did any character repeat a disproven rumor?
- Which source influenced the final arrest?

The Historian queries the live database through the official Managed MCP Server. It does not trust a summary generated by the game application.

This makes the Historian:

- A gameplay feature
- A technical proof
- An independent auditor
- A visible sponsor integration

## 11.3 ccloud CLI

Supporting role:

- Provision and inspect the cluster
- Capture machine-readable cluster configuration
- Export readiness evidence
- Include configuration snapshots in replay bundles

ccloud is supporting evidence, not a fake headline feature.

## 11.4 Agent Skills Repo

Optional supporting integration:

- Schema-readiness checks
- Retry and transaction guidance
- Deployment validation
- Reproducible readiness report

It is cut before any core game mechanic if schedule slips.

---

# 12. Why CockroachDB Is Structurally Necessary

A small single-player prototype could be built using another transactional database.

The production form of Hearsay requires more:

- Many NPC agents updating shared world state
- Multiple players influencing one persistent town
- Distributed semantic retrieval
- Transactional provenance
- Coherent concurrent updates
- Long-running world availability
- Eventual multi-region locality

The load-bearing requirement is:

> Multiple autonomous agents and players concurrently update a branching belief graph while active belief state, semantic memory, quest consequences, and provenance must agree transactionally.

The critical transaction commits:

- New belief version
- Transmission edge
- Active belief pointer
- Relationship change
- Quest or reputation consequence

Either all become visible, or none do.

A split operational-database and vector-database architecture creates a consistency window where:

- The relational belief is written but not searchable
- A superseded embedding remains retrievable
- A transmission edge exists without its belief
- A worker crash leaves partial state
- Semantic recall returns a version the game no longer considers active

The benchmark measures this specific architectural risk.

---

# 13. Data Model

Exact syntax should be validated against current CockroachDB documentation during implementation.

```sql
CREATE TABLE characters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name STRING NOT NULL UNIQUE,
  role STRING NOT NULL,
  persona JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name STRING NOT NULL,
  return_token_hash STRING,
  credibility FLOAT NOT NULL DEFAULT 0.5,
  first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE game_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id UUID NOT NULL REFERENCES players(id),
  scenario_key STRING NOT NULL,
  action_count INT NOT NULL DEFAULT 0,
  world_tick INT NOT NULL DEFAULT 0,
  status STRING NOT NULL DEFAULT 'active',
  ending_key STRING,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  player_id UUID NOT NULL REFERENCES players(id),
  character_id UUID NOT NULL REFERENCES characters(id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  sender_kind STRING NOT NULL,
  sender_id UUID,
  content STRING NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE propositions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  proposition_key STRING NOT NULL,
  subject_kind STRING NOT NULL,
  subject_id UUID,
  predicate STRING NOT NULL,
  canonical_ground_truth JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (game_run_id, proposition_key)
);

CREATE TABLE beliefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  proposition_id UUID NOT NULL REFERENCES propositions(id),
  holder_kind STRING NOT NULL,
  holder_id UUID NOT NULL,
  current_version INT NOT NULL DEFAULT 1,
  status STRING NOT NULL DEFAULT 'active',
  contested BOOL NOT NULL DEFAULT false,
  UNIQUE (game_run_id, proposition_id, holder_kind, holder_id)
);

CREATE TABLE belief_versions (
  belief_id UUID NOT NULL REFERENCES beliefs(id),
  version INT NOT NULL,
  narrative_text STRING NOT NULL,
  normalized_position JSONB NOT NULL,
  confidence FLOAT NOT NULL DEFAULT 0.5,
  salience FLOAT NOT NULL DEFAULT 1.0,
  embedding VECTOR(1024),
  source_kind STRING NOT NULL,
  source_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (belief_id, version)
);

CREATE TABLE transmissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  proposition_id UUID NOT NULL REFERENCES propositions(id),
  from_belief_id UUID REFERENCES beliefs(id),
  from_version INT,
  to_belief_id UUID NOT NULL REFERENCES beliefs(id),
  to_version INT NOT NULL,
  speaker_id UUID,
  listener_id UUID,
  original_text STRING,
  retold_text STRING NOT NULL,
  mutation_note STRING,
  trust_at_time FLOAT,
  model_id STRING,
  tick_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  evidence_key STRING NOT NULL,
  title STRING NOT NULL,
  description STRING NOT NULL,
  payload JSONB,
  discovered_by_player BOOL NOT NULL DEFAULT false,
  UNIQUE (game_run_id, evidence_key)
);

CREATE TABLE evidence_links (
  evidence_id UUID NOT NULL REFERENCES evidence(id),
  proposition_id UUID NOT NULL REFERENCES propositions(id),
  effect STRING NOT NULL,
  weight FLOAT NOT NULL,
  PRIMARY KEY (evidence_id, proposition_id)
);

CREATE TABLE relationships (
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  a_kind STRING NOT NULL,
  a_id UUID NOT NULL,
  b_kind STRING NOT NULL,
  b_id UUID NOT NULL,
  trust FLOAT NOT NULL DEFAULT 0.5,
  affinity FLOAT NOT NULL DEFAULT 0.5,
  fear FLOAT NOT NULL DEFAULT 0.0,
  last_interaction TIMESTAMPTZ,
  PRIMARY KEY (game_run_id, a_kind, a_id, b_kind, b_id)
);

CREATE TABLE gossip_ticks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  tick_number INT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  hops_attempted INT NOT NULL DEFAULT 0,
  hops_committed INT NOT NULL DEFAULT 0,
  serialization_retries INT NOT NULL DEFAULT 0,
  UNIQUE (game_run_id, tick_number)
);

CREATE TABLE decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_run_id UUID NOT NULL REFERENCES game_runs(id),
  decision_kind STRING NOT NULL,
  actor_id UUID NOT NULL,
  result JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE decision_inputs (
  decision_id UUID NOT NULL REFERENCES decisions(id),
  belief_id UUID NOT NULL REFERENCES beliefs(id),
  belief_version INT NOT NULL,
  influence_weight FLOAT,
  PRIMARY KEY (decision_id, belief_id, belief_version)
);

CREATE TABLE benchmark_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  architecture_arm STRING NOT NULL,
  seed INT NOT NULL,
  recall_accuracy FLOAT,
  lineage_completeness FLOAT,
  stale_retrieval_rate FLOAT,
  partial_write_rate FLOAT,
  contradiction_rate FLOAT,
  report_s3_key STRING,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

# 14. Vector Retrieval Pattern

Vector retrieval should be implemented as a two-stage process.

First, use the vector index to find semantically relevant candidates within exact prefixes such as character and status. Then join relational context and rerank.

Illustrative pattern:

```sql
WITH candidates AS (
  SELECT
    bv.belief_id,
    bv.version,
    bv.narrative_text,
    bv.embedding <=> $query_embedding AS distance
  FROM belief_versions bv
  JOIN beliefs b ON b.id = bv.belief_id
  WHERE b.holder_id = $character_id
    AND b.status = 'active'
    AND bv.version = b.current_version
  ORDER BY bv.embedding <=> $query_embedding
  LIMIT 30
)
SELECT
  c.belief_id,
  c.version,
  c.narrative_text,
  (1 - c.distance)
    * bv.salience
    * bv.confidence
    * COALESCE(r.trust, 0.5) AS final_score
FROM candidates c
JOIN belief_versions bv
  ON bv.belief_id = c.belief_id
 AND bv.version = c.version
LEFT JOIN relationships r
  ON r.game_run_id = $game_run_id
 AND r.a_id = $character_id
 AND r.b_id = bv.source_id
ORDER BY final_score DESC
LIMIT 8;
```

During the technical demo, show:

- The real query
- The vector index
- `EXPLAIN`
- The retrieved belief versions
- Their provenance links

---

# 15. Transaction Patterns

## 15.1 Conversation-to-belief transaction

A player message may create or update a character belief.

The model call occurs outside the database transaction.

The transaction then:

1. Validates the character’s current belief version.
2. Inserts the new belief version.
3. Advances the active version pointer.
4. Records the player as the source.
5. Updates relationship state.
6. Records any immediate quest consequence.

All writes commit together.

## 15.2 Gossip transmission transaction

```text
Read speaker belief version
    ↓
Generate retelling outside transaction
    ↓
Begin serializable transaction
    ↓
Validate speaker version is unchanged
    ↓
Read listener's current belief for the proposition
    ↓
Insert listener belief version
    ↓
Insert transmission edge
    ↓
Advance listener current-version pointer
    ↓
Update relationship and salience
    ↓
Commit
```

On serialization failure:

- Reread current state
- Re-evaluate deterministic conflict policy
- Retry with bounded exponential backoff
- Count retries as visible evidence

## 15.3 The signature concurrent race

This is the main database proof.

Scenario:

1. Elias currently holds belief version 4 about the relic theft.
2. Marta and Bram simultaneously send conflicting updates.
3. Both operations read version 4.
4. Both generate a proposed next belief.
5. One transaction commits first.
6. The other detects the changed version.
7. It rereads the new state.
8. The system records the second claim as a contested input or produces a new coherent version according to the conflict policy.
9. Both source histories remain intact.
10. Elias has one valid active state.

The demo shows:

- Two source claims
- Shared previous version
- Transaction retry
- Complete provenance
- One coherent active belief

---

# 16. Deterministic Rules and LLM Boundaries

The model should not own game truth or transaction policy.

## 16.1 LLM responsibilities

Amazon Bedrock models handle:

- Natural dialogue
- Structured proposition extraction
- Controlled rumor retelling
- Summarization
- Contradiction classification
- Character voice
- Explanation text

## 16.2 Deterministic system responsibilities

Code and database rules handle:

- Ground truth
- Win and loss conditions
- Turn count
- Evidence weights
- Trust updates
- Active belief version
- Conflict policy
- Transaction retries
- Quest state
- Provenance
- Reputation thresholds
- Final arrest decision structure

## 16.3 Structured outputs

Every model response that affects state uses a schema.

Example rumor mutation output:

```json
{
  "retold_claim": "The harbormaster hid the chapel key.",
  "semantic_position": {
    "suspect": "harbormaster",
    "action": "hid",
    "object": "chapel key"
  },
  "drift_note": "Changed 'silver key' to 'chapel key' based on current quest context.",
  "confidence_delta": -0.08
}
```

Invalid output is rejected and retried or replaced with a deterministic fallback.

---

# 17. AWS, Embeddings, and Hosting Architecture

## 17.1 CockroachDB Cloud

CockroachDB Cloud provides the hosted database instance and the entire persistent-memory substrate.

It stores:

- Players and game runs
- Propositions
- Character beliefs
- Immutable belief versions
- Rumor transmissions
- Relationships and trust
- Evidence
- Decisions and decision inputs
- Locally generated vector embeddings and indexes
- Benchmark metadata

CockroachDB is not hosted inside the application server and is not replaced by S3 or Modal.

## 17.2 Amazon Bedrock

Amazon Bedrock is used only for LLM capabilities:

- Character dialogue
- Structured proposition extraction
- Controlled rumor mutation
- Contradiction analysis
- Natural-language explanations

Bedrock does not generate embeddings and does not host the game server, frontend, scheduler, database, or artifacts.

## 17.3 Local embedding model

All memory and query embeddings are generated by a local embedding model.

Default placement:

- Runs on the same EC2 or application host as the game backend, or
- Runs as a separate lightweight local embedding service

Possible model families include compact sentence-transformer or BGE-style models, selected during implementation based on:

- Retrieval quality
- Embedding dimension
- CPU latency
- Memory footprint
- Licensing
- Compatibility with CockroachDB vector indexing

The exact model must be named in the final submission.

## 17.4 Optional Modal usage

Modal may be used only if embedding generation or another auxiliary workload genuinely benefits from GPU acceleration.

Valid uses include:

- Hosting the local embedding model on GPU
- Batch embedding generation
- Benchmark acceleration
- Offline model evaluation

Modal is not part of the required AWS-service story.

If unused, remove it from the final Devpost description and architecture diagram.

## 17.5 Amazon S3

Amazon S3 is used only for non-operational artifacts:

- Frozen benchmark reports
- Replay bundles
- Scenario seeds
- Exported rumor graphs
- Architecture images
- Demo evidence
- Submission artifacts

S3 is not used as the live game database or canonical memory store.

## 17.6 Application hosting

The frontend, game API, deterministic rules engine, gossip scheduler, background jobs, and default local embedding service may run on:

- Amazon EC2, or
- Another suitable general-purpose application host

The final submission should name the actual host used.

## 17.7 Services not claimed

Unless they are actually implemented, Hearsay does not claim:

- AWS Lambda
- Amazon ECS
- Amazon EventBridge
- Amazon CloudWatch
- Amazon SageMaker
- Any AWS embedding service
- Any additional AWS storage or compute service

The architecture should remain truthful and easy for judges to verify.


# 18. The World Coherence Benchmark

The benchmark must test a specific architectural claim rather than attack a vague “normal vector database.”

## 18.1 Architecture arms

| Arm | Description |
|---|---|
| Context-only NPC | Character receives only recent conversation context; no persistent belief system |
| Asynchronous dual-store memory | Relational belief state and vector search are updated through separate asynchronous paths |
| CockroachDB unified memory | Beliefs, versions, provenance, quest state, and vectors are committed and queried in one transactional system |

## 18.2 Dual-store fault model

The dual-store arm explicitly injects:

- Delayed embedding updates
- Worker crash between relational and vector writes
- Duplicate event delivery
- Out-of-order event processing
- Retrieval of superseded embeddings
- Concurrent last-write-wins updates

All parameters are published.

At zero delay and no injected failures, the dual-store system should approach the unified implementation.

The benchmark is not designed to claim that every other database is incorrect. It demonstrates the consistency risks of splitting semantic and operational memory.

## 18.3 Protocol

- Fixed mystery seed
- Fixed character trust graph
- Fixed ground truth
- Approximately 40 authored propositions
- Approximately 150 scripted rumor transmissions
- Deliberate conflicting updates
- Multiple fixed random seeds
- Automated interrogation phase

Questions include:

- Who does Elias currently suspect?
- What source first connected Bram to the chapel?
- Which version of the silver-key rumor is active?
- Can the full lineage be traced to an origin?
- Did semantic retrieval return a superseded belief?
- Which beliefs influenced the final arrest?

## 18.4 Metrics

- Recall accuracy
- Lineage completeness
- Stale retrieval rate
- Partial write rate
- Contradiction rate
- Lost update count
- Decision reproducibility
- Correct final accusation rate

## 18.5 Output

The submission includes:

- One clean comparison chart
- Frozen JSON reports in S3
- Public seeds
- Reproducible runner
- Fault configuration
- Raw event logs
- A short explanation of limitations

---

# 19. Game UI

## 19.1 Main town view

- Compact illustrated town map
- Current time
- Remaining actions
- Player credibility
- Current objective
- Character availability
- Key discovered evidence

## 19.2 Conversation view

- Character portrait
- Dialogue
- Recent relationship changes
- Optional action choices
- Evidence presentation
- No technical database details

## 19.3 Rumor map

A game-facing social view showing:

- Who currently knows a proposition
- Who trusts whom
- How far a rumor has spread
- Which versions are contested
- Whether a rumor can be traced to the player

Do not reveal all hidden information during normal play.

## 19.4 Town Historian

A separate post-game or judge-facing surface.

It includes:

- Managed MCP chat
- Complete belief lineage
- Text diff across retellings
- Transaction timestamps
- Active and superseded versions
- Decision inputs
- Vector retrieval explanation
- Benchmark links

## 19.5 The Director's Room (judge-facing ops console)

A separate surface, linked from the README as "for judges and engineers." The game never shows infrastructure; the Director's Room shows nothing else. It is the bridge between fiction and proof.

**The centerpiece: a real worker kill.**

- A **Kill Gossip Worker** button sends an actual SIGKILL to the live tick process — if possible mid-hop, between the LLM retelling call and the transaction commit.
- Live status strip: worker down → supervisor restarts it → next tick resumes.
- Immediately after recovery, an automatic Historian audit runs and displays:
  - transmission edges without a resulting belief: **0**
  - belief versions without lineage: **0**
  - superseded versions still marked active: **0**
  - the interrupted hop: either fully committed or cleanly absent — never partial
- This is the dual-store fault model (crash between writes) demonstrated live as a **non-event** on the unified system. It is an *application* kill: zero managed-cloud risk, zero resemblance to infrastructure-resilience entries.

**Hard rule: the kill is real or it does not exist.** No simulated animations, no mocked status. The button is rate-limited with a cooldown and audit-logged.

Also housed here:

- The full rumor graph (unredacted, unlike the in-game rumor map)
- Benchmark chart with links to frozen S3 reports and seeds
- ccloud cluster configuration captures
- Replay bundle download
- Cost telemetry

**Optional diegetic wink:** after a kill and recovery, the game view may show the town clock stutter or an NPC remark on "strange weather." The wink is flavor; the proof lives here.

## 19.6 End screen

Shows:

- Culprit arrested
- Player credibility
- Innocents harmed
- Rumors planted
- Rumors corrected
- Longest rumor chain
- Most influential character
- Exact beliefs that caused the ending
- Alternate ending teaser

---

# 20. Three-Minute Demo Plan

## 0:00–0:12 — Cold open

The constable says:

> “You should not have told Marta about the silver key.”

The player responds:

> “I never told you.”

Immediate question:

> How did he learn it?

## 0:12–0:32 — Start the rumor

Show the earlier conversation with Marta.

The player says:

> “I saw the harbormaster bury a silver key.”

Advance the town clock.

## 0:32–0:58 — Rumor mutation

Show three short gossip hops.

```text
buried a silver key
→ hid a treasury key
→ stole the chapel key
```

The rumor map expands.

## 0:58–1:20 — Gameplay consequence

The distorted rumor changes:

- Elias’s suspect ranking
- Player access to the docks
- A new accusation option
- Bram’s attitude toward the player

This proves memory is gameplay, not flavor text.

## 1:20–1:45 — Concurrent conflict

Marta and Bram simultaneously give Elias conflicting updates.

Show:

- Both starting from Elias belief version 4
- One transaction committing
- One retrying
- Both provenance paths preserved
- One coherent active belief

## 1:45–2:08 — Historian proof

Ask the Town Historian:

> “How did Elias learn about the key, and which version influenced his accusation?”

The Managed MCP agent reconstructs:

- Origin message
- Every transmission
- Text changes
- Current active version
- Decision dependency

## 2:08–2:24 — Player resolves the case

The player presents physical evidence to Talia or Elias. The town’s dominant belief shifts. The correct culprit is arrested.

## 2:24–2:45 — The Director's Room

Cut to the judge-facing console:

- **Kill Gossip Worker** pressed mid-tick — real SIGKILL on screen
- Worker restarts; audit lands: **0 partial writes, 0 orphaned transmissions, 0 stale actives**
- The benchmark chart lands beside it: context-only vs asynchronous dual-store vs CockroachDB unified memory — stale retrieval, lineage completeness, correct final accusation

One sentence of narration: "The crash you just watched is the exact fault the dual-store arm suffers from — here it is a non-event."

## 2:45–3:00 — Close

> “Most AI characters remember a conversation.”

> **“Hearsay remembers a society.”**

Display:

- Live URL
- GitHub
- CockroachDB tools
- AWS services

---

# 21. Minimum Viable Winning Build

## 21.1 Must build

- One complete mystery
- Eight authored characters
- Twelve-action game loop
- Persistent player identity
- Structured propositions
- Character-specific beliefs
- Immutable belief versions
- Transmission lineage
- Trust and credibility
- Controlled gossip ticks
- Real vector retrieval
- Concurrent belief-update race
- Managed MCP Historian
- Rumor lineage visualization
- Deterministic ending
- Three-arm benchmark
- **Director's Room with real gossip-worker kill and zero-partial-state audit**
- **Per-player instancing + Town Ledger (thin shared cross-visitor layer)**
- **Idle drift ticks (slow wall-clock gossip so the town talks while you're away)**
- Public repository
- Live playable demo
- Sub-three-minute video

## 21.2 Strong bonus

- Second mystery
- Asynchronous shared public town
- Return-player epilogue
- Multiple endings
- Faction memory
- S3 replay download
- Accessibility polish
- Cost telemetry
- Multi-region design notes
- Scenario editor

## 21.3 Cut if late

- Town map animation
- More than eight characters
- Second mystery
- Character schedules
- Rich inventory
- Background idle thoughts
- Voice input
- Multiplayer
- Multi-region deployment
- Agent Skills contribution
- Complex salience decay

## 21.4 Do not build

- Real-time combat
- 3D world
- Open-ended infinite simulation
- Twenty generic characters
- Database node-kill or region-kill theatrics (the **worker-process kill in the Director's Room is required and real**; infrastructure kills are out — they are risky on managed cloud and imitate resilience-category entries)
- Any simulated or animated "kill" of any kind — if a button does not kill a real process, the button does not exist
- Full MMORPG backend
- LLM-controlled ground truth
- Generic agent-memory SDK
- A dashboard-first experience
- A fake eventual-consistency baseline

---

# 22. Execution Plan

**Standing item — every Friday until submission:** competitor reconnaissance. Re-scan GitHub for new entrants, check the Devpost gallery once it publishes, and re-test our beats against any new frontrunner. If another experiential/game entry appears, differentiation shifts to the belief-graph mechanics, the worker-kill audit, and the benchmark — the hardest parts to copy quickly.

## Week 1 — Core game and memory

- Repository, license, deployment skeleton
- CockroachDB Cloud cluster
- Character and scenario seeds
- Proposition, belief, version, and transmission schema
- Minimal dialogue with two characters
- Bedrock structured outputs
- Vector retrieval spike
- One complete rumor chain
- Barebones playable UI

**Exit condition:** The player tells one character something, advances the town, and another character later recalls a mutated version with complete lineage.

## Week 2 — Complete mystery

- All eight characters
- Twelve-action game loop
- Evidence and reputation mechanics
- Gossip tick selection
- Trust updates
- Deterministic endings
- Player return identity
- Playtest and dialogue tuning

**Exit condition:** A stranger can complete the mystery and understand why they won or lost.

## Week 3 — Technical proofs

- Managed MCP Historian
- Concurrent update race
- Decision-input tracking
- Rumor graph and mutation diffs
- Director's Room console: real worker SIGKILL, supervisor restart, automatic zero-partial-state audit
- Town Ledger (cross-instance) + Historian query over it
- Idle drift tick scheduler
- Benchmark arms
- Fault injection
- Frozen benchmark results

**Exit condition:** The Historian reconstructs the final accusation, the worker kill is a demonstrated non-event with a zero-partial-state audit, and the benchmark produces reproducible numbers.

## Week 4 — Polish and submission

- Visual polish
- Character portraits
- README
- Architecture diagram
- Cost controls
- Moderation
- Replay bundles
- Demo recording
- Judge-flow rehearsals

**Exit condition:** The complete story works three times from a clean browser without manual repair.

## Final buffer

- No new features
- Re-run benchmark
- Freeze numbers
- Re-record stale footage
- Test live URL
- Submit one day early

---

# 23. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Feels like eight chatbots | Fatal | Clear objective, limited actions, evidence, consequences, endings |
| Rumor mutation becomes nonsense | High | Structured propositions, controlled mutation, semantic validation |
| NPC dialogue ignores memory | High | Retrieve small, relevant, character-specific memory sets |
| CockroachDB role appears optional | Fatal | Concurrent shared-belief race, unified vector + provenance benchmark |
| Benchmark is a strawman | High | Publish fault model; allow zero-fault dual-store control |
| Mystery is not fun | High | Author one strong scenario; playtest early |
| Too much LLM randomness | High | Deterministic game state and fallback rules |
| Public abuse | Medium | Moderation, fictional-content guidance, rate limits |
| Bedrock cost | Medium | Action limits, compact prompts, smaller gossip model |
| Historian looks canned | High | Real read-only MCP queries over live state |
| Judges suspect the kill is staged | High | Real SIGKILL, live status, automatic zero-partial-state audit; hard rule: no simulated kills anywhere |
| Another experiential/game entry appears late | Medium | Weekly Friday recon; moats are the belief graph, worker-kill audit, and benchmark |
| Schema becomes overcomplex | Medium | One proposition model, one active belief per holder |
| Multiplayer derails scope | High | Single-player MVP; asynchronous multiplayer only as stretch |

---

# 24. Judge Objections

## “Isn’t this just an AI Town clone?”

Existing AI towns primarily demonstrate autonomous characters, memory retrieval, and emergent interaction.

Hearsay’s contribution is a specific game and memory mechanism:

- Per-character positions on shared propositions
- Immutable belief versions
- Branching rumor transmission
- Social trust
- Concurrent conflicting updates
- Decision provenance
- Independent forensic audit

The player strategically manipulates the belief network to solve a mystery.

## “Why is this a game rather than a technology demo?”

The memory system changes:

- Dialogue access
- Reputation
- Suspect ranking
- Evidence credibility
- The final arrest
- Persistent future reactions

Without memory, the central mechanic disappears.

## “Could this be built on PostgreSQL?”

A small single-region prototype could — including on Postgres with pgvector, which also offers serializable transactions with vectors and relations in one commit. We do not pretend otherwise; pretending would cost credibility with exactly the judges who matter.

The honest answer has three parts:

1. **The two load-bearing tools have no pgvector equivalent.** Distributed Vector Indexing sits in the production recall path, and the Managed MCP Server powers an independently authenticated, read-only Historian that audits the live database without touching application code. Remove CockroachDB and both the recall architecture and the forensic character disappear, not just the hosting.
2. **The demonstrated failure mode is architectural, not brand-versus-brand.** The benchmark's dual-store arm measures what actually happens on the stack teams reach for when a single Postgres node stops being enough: split operational and semantic stores with asynchronous sync. Stale retrieval, broken lineage, and partial writes are on the chart. And the Director's Room shows the same crash-between-writes fault, injected live against the unified system, as a non-event with a zero-partial-state audit.
3. **The product's stated form is a persistent shared world** — many agents, many players, the Town Ledger spanning every visitor, always-on availability, and a multi-region locality path. That form needs distributed serializable SQL; a single-primary node is a prototype ceiling, and we present it as exactly that.

The benchmark does not claim PostgreSQL lacks transactions. It measures the specific risks of splitting semantic and operational memory — and the live kill shows the unified system refusing to exhibit them.

## “How do you prevent LLM hallucinations from breaking the game?”

Ground truth, evidence, trust updates, win conditions, and active-state transitions are deterministic. The model controls language and structured interpretation within validated schemas.

## “What is the measurable outcome?”

- Correct final accusation
- Recall accuracy
- Complete rumor lineage
- Stale retrieval rate
- Contradiction rate
- Lost or partial state
- Decision reproducibility
- Player outcome consistency

## “Why does the Historian need MCP?”

The Historian is independently authenticated and read-only. It inspects the actual live state rather than repeating the game server’s explanation.

This turns MCP into an auditor and gameplay feature, not a development convenience.

---

# 25. Submission Copy

## Project description

Hearsay is a social mystery game set in a town where NPCs gossip when the player is not around. Every character remembers a different version of events, every retelling can mutate, and every important decision can be traced back to the conversations that caused it.

The player has one day to solve the theft of a sacred relic. They investigate eight characters, reveal or conceal evidence, plant or correct rumors, build trust, and shape what the town believes before the royal inspector arrives.

CockroachDB stores the world’s shared belief graph: propositions, per-character beliefs, immutable versions, transmission lineage, social relationships, quest state, and semantic embeddings. Distributed Vector Indexing powers character recall. Serializable transactions preserve coherent belief state when conflicting reports arrive concurrently. An independent Town Historian queries the live database through the CockroachDB Cloud Managed MCP Server and reconstructs exactly who told whom, how a rumor changed, and which beliefs caused the final arrest.

Amazon Bedrock powers character dialogue, structured claim extraction, and rumor retelling; a local model generates embeddings. the application runtime runs gossip ticks, while S3 stores benchmark reports and replay bundles.

A reproducible World Coherence Benchmark compares context-only NPCs, asynchronous dual-store memory, and CockroachDB unified memory across recall accuracy, stale retrieval, lineage completeness, and correct final accusation rate.

Most AI characters remember a conversation.

Hearsay remembers a society.

## Short description

A social mystery game where NPCs gossip, lies spread, reputations persist, and every rumor has a traceable history.

## One-line technical explanation

A persistent AI game world built on a transactional, versioned social-belief graph with semantic recall and independently auditable provenance.

---

# 26. README Opening

```markdown
# Hearsay

**The truth is what survives the telling.**

Hearsay is a social mystery game where NPCs gossip when you are not around.
Every character remembers a different version of events, every rumor has a
traceable family tree, and the town's final belief state determines whether
you solve the case.

🎮 Play the mystery: <LIVE URL>

## The hook

Tell the innkeeper a secret.

Advance the town clock.

Three conversations later, the constable confronts you with a distorted
version of your own story.

Then ask the Town Historian:

> How did he learn that?

The Historian reconstructs the exact origin, every retelling, every mutation,
and the belief version that influenced the constable's decision—through the
official CockroachDB Cloud Managed MCP Server.

## Why CockroachDB

Hearsay stores semantic memory, social relationships, belief versions,
transmission lineage, quest state, and decision provenance in one distributed
transactional system.

When two characters simultaneously deliver conflicting reports to the same
NPC, CockroachDB preserves both histories while keeping one coherent active
belief.
```

---

# 27. Final Checklist

## Game

- [ ] One complete mystery
- [ ] Eight distinct characters
- [ ] Limited actions and visible clock
- [ ] Clear win and loss conditions
- [ ] Evidence changes outcomes
- [ ] Lies are viable but risky
- [ ] Rumors create visible consequences
- [ ] Ending is determined by belief state
- [ ] Per-player instancing verified (two simultaneous fresh sessions do not interfere)
- [ ] Town Ledger records cross-visitor outcomes; Historian can cite it
- [ ] Idle drift ticks run on wall-clock schedule with cost caps

## Memory

- [ ] Propositions separate from beliefs
- [ ] One active belief per holder and proposition
- [ ] Immutable belief versions
- [ ] Complete transmission lineage
- [ ] Character-specific vector recall
- [ ] Trust and credibility influence belief updates
- [ ] Decisions store exact belief-version inputs

## Sponsor proof

- [ ] Distributed Vector Indexing in production path
- [ ] Managed MCP Historian over live state
- [ ] Real concurrent update race
- [ ] Serializable retry visible
- [ ] Real gossip-worker SIGKILL in Director's Room; zero-partial-state audit displayed
- [ ] No simulated or animated kills anywhere in game, console, or video
- [ ] Unified-memory benchmark
- [ ] CockroachDB Cloud instance is the canonical memory database
- [ ] Amazon Bedrock is load-bearing for LLM inference only
- [ ] Local embedding model is named and reproducible
- [ ] Embedding service location is documented
- [ ] Amazon S3 stores benchmark and replay artifacts
- [ ] No unimplemented AWS services are claimed
- [ ] Final application host is named accurately
- [ ] Modal is mentioned only if actually used

## Reliability

- [ ] Structured model outputs validated
- [ ] Deterministic fallback path
- [ ] No LLM calls inside open transactions
- [ ] Rate limits and cost caps
- [ ] Moderation enabled
- [ ] Demo works from clean browser
- [ ] Benchmark reproducible

## Submission

- [ ] Public repository and open-source license
- [ ] Live playable demo URL
- [ ] Public YouTube or Vimeo video under three minutes
- [ ] Video visibly demonstrates the CockroachDB memory layer
- [ ] CockroachDB tool-usage section names every tool and its real agent behavior
- [ ] AWS service-usage section names every service and its concrete role
- [ ] Architecture diagram included
- [ ] CockroachDB implementation feedback included
- [ ] README leads with gameplay hook
- [ ] Reproducible benchmark and frozen reports linked
- [ ] Real numbers, no fabricated results
- [ ] Submitted before the final day

---

# 28. Brutal Success Standard

Hearsay has winner potential only if all of the following are true:

1. It feels like a game, not a collection of chatbots.
2. A rumor visibly changes gameplay.
3. The rumor graph is immediately understandable.
4. The player can intentionally manipulate information.
5. CockroachDB prevents a real shared-state inconsistency.
6. The Historian independently proves the lineage.
7. The benchmark is honest and reproducible.
8. The demo tells one coherent story in under three minutes.

The project should be abandoned or radically narrowed if:

- The mystery is not fun without the technical explanation.
- NPCs fail to use memories naturally.
- Rumor mutation cannot remain coherent.
- The concurrent update appears artificially staged.
- The CockroachDB implementation can be replaced without changing the core guarantee.
- The full player-action → rumor → consequence → Historian loop cannot be demonstrated reliably.

The final strategic sentence is:

> **Do not build a town that happens to remember. Build a game where controlling memory is how the player wins.**
