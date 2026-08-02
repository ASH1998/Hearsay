# Hearsay story, agents, and memory roadmap

Last updated: 2026-07-31

This roadmap translates the Game Design Document into the next implementation
slices. The Game Design Document remains authoritative for the player
experience. The Hackathon Blueprint remains authoritative for CockroachDB, AWS,
proof, benchmark, and submission requirements.

## Product outcome

The hackathon build must feel like a town of people acting on different
memories, not a fixed quest with AI dialogue attached. A judge should see this
loop without opening developer tools:

1. The player makes a consequential claim or promise.
2. A named NPC recalls their own CockroachDB memory.
3. Claude Haiku 4.5 on Amazon Bedrock chooses one bounded social action.
4. The action is validated and committed with its memory consequence.
5. Another resident behaves differently because the memory reached them.
6. The Historian reconstructs the exact source and mutation chain.
7. The election exposes which remembered claims changed the result.

CockroachDB is the canonical world and memory store. Bedrock is stateless
inference. S3 stores immutable replay and benchmark artifacts, never live game
memory.

## Featured story agents

| Agent | Dramatic want | Memory bias | Signature autonomous behavior | Story payoff |
|---|---|---|---|---|
| Marta Vale | Keep the inn supplied without surrendering the town to Bram | Promises and observed reliability outweigh gossip | Seeks help, verifies outcomes, and tells trusted regulars whether a promise was kept | Her endorsement or disappointment establishes the player's public character |
| Bram Coyle | Preserve commercial leverage and social importance | Threats and challenges remain highly salient; flattery is overvalued | Reframes disputes as attacks on order and recruits market allies | His version can make the player look capable, dishonest, or dangerous |
| Pip Marr | Be first with the story everyone repeats | Novelty and social reach outweigh source quality | Selects a nearby listener and sharpens a public rumor for transmission | His mutation becomes the clearest visible memory chain |
| Talia Fen | Protect private care from public panic | Firsthand evidence and confidentiality outweigh popularity | Reacts to leaked private facts and quietly corrects harmful claims | The player proves whether information can be handled responsibly |
| Rhea Kest | Keep political control while appearing indispensable | Influence and institutional loyalty outweigh outsider testimony | Offers bargains, tests coalitions, and responds to the current public belief state | The final compact forces the player to choose legitimacy or expedience |

## Runtime contract

Each consequential story boundary schedules a bounded agent turn:

```text
PERCEIVE  authoritative location, nearby residents, event, goals, relationships
RECALL    holder-scoped CockroachDB vector query plus relational reranking
DECIDE    one strict-schema Claude Haiku 4.5 action from the allowlist
VALIDATE  reject invented targets, entities, effects, and unavailable actions
ACT       speak, share, react, move, or wait
COMMIT    turn, event, memory version, transmission, projection, and provenance
RENDER    named action, changed wording, memory cue, and CockroachDB proof
```

The production path should select one featured agent and at most two listeners
per tick. This keeps latency and Bedrock cost bounded while making each turn
legible. Deterministic fallback remains valid for local tests but must be
visibly labeled and must not be presented as Bedrock proof.

## CockroachDB responsibilities

The existing belief spine remains the foundation: `propositions`, `beliefs`,
immutable `belief_versions`, `active_memories`, `transmissions`,
`relationships`, `retrieval_traces`, events, promises, election votes, and
belief-backed vote inputs.

The next schema slice should add only state that cannot be represented cleanly
today:

- `agent_goals`: authored goal, priority, status, and story availability.
- `agent_turns`: perceive/recall/decide/act audit with selected memory versions,
  provider/model/tokens, validation result, and committed event.
- `story_beats`: durable beat availability and resolution, derived from world
  state rather than a browser-only quest stage.
- `artifact_exports`: S3 object key, SHA-256, ETag, version ID, size, and status.

Every Bedrock prompt must be rehydrated from these CockroachDB-backed facts.
Every accepted outcome must return to CockroachDB through a bounded serializable
transaction. S3 and browser state cannot restore or invent agent continuity.

## Story spine for the focused release

The current election arc remains the release story because it matches the Game
Design Document and already has explainable consequences:

1. Marta asks for help with the blocked shipment.
2. The player makes or refuses a promise.
3. Bram forces a confrontation with four social approaches.
4. Pip chooses a listener and mutates the encounter into a public story.
5. Marta recalls the promise and changes her treatment of the player.
6. Talia tests whether the player protects a private truth or weaponizes it.
7. Rhea invites the player into the election and exposes the ballot-custody
   conflict.
8. The player challenges the system or accepts Rhea's compact.
9. Featured agents take a final memory-conditioned turn.
10. Twenty voters resolve the election from durable, cited inputs.

The next narrative work is depth inside these beats, not another disconnected
quest: give each featured agent a clear goal, a private fact, a public stance,
one relationship they can influence, and one remembered fact that changes a
later action.

## Delivery sequence

### Slice A — Visible proof

- Keep the in-world speaker-to-listener gossip bubble in the focused build.
- Label the Bedrock/deterministic decision provenance and CockroachDB commit.
- Surface recalled belief/version IDs in memory-conditioned conversations.
- Show the new Historian hop immediately after a retelling.

Gate: a first-time player can point to who acted, what they remembered, what
changed, and where it persisted.

### Slice B — Five real agent turns

- Generalize the Pip-only decision path into one shared featured-agent runtime.
- Retrieve the acting NPC's memories from CockroachDB before every decision.
- Persist an `agent_turns` audit row and selected memory references.
- Give Marta, Bram, Pip, Talia, and Rhea distinct allowlists and goal weights.

Gate: all five agents take at least one bounded, memory-conditioned action in a
normal eighteen-action run, and those turns survive API/browser restart.

### Slice C — Story consequences

- Store story-beat availability and resolution in CockroachDB.
- Let agent turns unlock, close, or reframe later choices through deterministic
  validated effects.
- Ensure at least one remembered action from each featured agent reaches an
  election input or changes another featured agent's treatment.

Gate: removing the CockroachDB memory layer breaks story continuity in an
obvious, honest way.

### Slice D — AWS evidence

- Configure the deployed inference path for Claude Haiku 4.5 through Bedrock.
- Export a redacted completion replay to a private versioned S3 bucket.
- Persist artifact metadata in CockroachDB and provide a short-lived download.
- Capture real Managed MCP and distributed-vector-index proof.

Gate: one deployed run visibly proves Bedrock inference, CockroachDB recall and
lineage, Managed MCP history, and an S3 replay artifact without overstating any
fallback path.
