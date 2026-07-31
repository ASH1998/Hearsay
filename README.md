# Hearsay

**The truth is what survives the telling.**

Hearsay is a browser-based social-memory game set in Greyhaven. You have three
days to win a mayoral election in a town where promises become rumors, rumors
mutate as people repeat them, and every decisive memory keeps its provenance.

The default first playthrough is a full-screen, top-down playable town. Walk
Greyhaven directly, approach residents under the gold objective marker, and
hear rumors change while you move. The compact world HUD sits over an
authoritative FastAPI simulation with durable CockroachDB memory, schedules,
promises, town events, and an explainable 20-resident election.

## Local setup

Hearsay is pinned to Node 22 and pnpm 11.9.0. On Windows, activate the
repository's exact package-manager version once:

```powershell
corepack install --global pnpm@11.9.0
pnpm --version
```

The version check must print `11.9.0`. Then:

```powershell
pnpm bootstrap
pnpm doctor
pnpm play
```

If another global pnpm installation still shadows Corepack, no uninstall is
required. Use the pinned launcher directly:

```powershell
corepack pnpm@11.9.0 play
```

Then open `http://localhost:3000`. The API serves health and OpenAPI
documentation at `http://localhost:8000/health` and
`http://localhost:8000/docs`.

`pnpm play` creates a bounded production build and serves it without Next.js
development controls or a persistent compiler. The build is stopped if it
exceeds 60 seconds, and Ctrl+C cleans up the exact web/API processes started by
the command. Use `pnpm dev` only while editing source; it uses the tested
Webpack watcher, hides the development indicator from the game surface, rejects
duplicate port 3000 servers, and follows the same owned-process cleanup rule.

### How to play

1. Select **Take the road to Greyhaven**. Marta immediately gives you the first
   problem, so there is no menu to decipher.
2. Use **WASD** or the **arrow keys** to walk toward the gold marker.
3. Press **T**, **Enter**, or **Space** when the proximity prompt names the
   resident you need.
4. Follow the single sentence in the top-left objective card. Press **J** only
   when you want the optional journal.

The guided route is Marta → Bram → Marta → Talia → Rhea → election night. The
first run is ten consequential choices; walking and exploration are free.
Refreshing restores the current run. To deliberately discard an older save,
press **J** and choose **Restart first playthrough**.

The focused first-playthrough check starts isolated deterministic servers,
plays the exact ten-action release path, and always shuts those servers down:

```powershell
corepack pnpm@11.9.0 test:e2e:release
```

To use Cockroach Cloud on Windows, put either `DATABASE_URL` or the exported
`username`, `password`, `command_to_create_cert`, and `command_to_connect`
values in the ignored `.env`, then enable the durable backend:

```dotenv
HEARSAY_PERSISTENCE_BACKEND=cockroachdb
```

```powershell
corepack pnpm@11.9.0 db:migrate
corepack pnpm@11.9.0 db:test
```

The migration and test commands translate Cockroach Cloud's certificate command
to the Windows PostgreSQL certificate location. Database tests create and clear
only `hearsay_test`; the application uses `hearsay`. This repository uses the
user-managed Cockroach Cloud instance configured in the ignored `.env`; it does
not require a local Docker database.

The Town Historian has a separate server-side Managed MCP credential. Create a
Cockroach Cloud service-account API key for the Historian and copy the cluster
ID from the Cloud Console overview URL, then add:

```dotenv
HEARSAY_HISTORIAN_PROVIDER=managed_mcp
COCKROACH_MCP_CLUSTER_ID=your-cluster-id
COCKROACH_MCP_API_KEY=your-independent-api-key
```

The Historian connects to Cockroach Labs' official
`https://cockroachlabs.cloud/mcp` endpoint, dynamically verifies the
`select_query` input schema, and exposes only a fixed lineage query. No raw SQL
or MCP tool name comes from the browser. In `auto` mode, missing or failed MCP
authentication keeps the game usable through a clearly labeled direct-database
fallback; that response always carries `sponsor_proof=false` and is not valid
hackathon MCP evidence.

The proof command is intentionally one-shot. Its default mode is a local
configuration check with no external request. The explicit fixture mode writes
a deterministic two-action run only to `hearsay_test`, performs one Managed MCP
tool discovery and one read-only `select_query`, records the audit, and exits:

```powershell
tools/uv/uv.exe run python scripts/check_historian.py
tools/uv/uv.exe run python scripts/check_historian.py --execute --trace-fixture
```

Cloud credentials are optional. With
`HEARSAY_PERSISTENCE_BACKEND=memory`, the API uses an explicit deterministic
development fallback; it never silently switches authoritative state.

Inference defaults to `HEARSAY_LLM_PROVIDER=fallback`, so starting the local
application cannot invoke a paid model. The deployed path must explicitly set
`HEARSAY_LLM_PROVIDER=bedrock`, `AWS_REGION`, and
`HEARSAY_BEDROCK_MODEL`. Bedrock uses the Converse API with a configured Claude
model or inference profile, a constrained JSON Schema response, lazy client
creation, bounded retries, and deterministic fallback. Provider, model,
latency, attempts, fallback state, and token usage are stored with the
transmission when available. Modal remains an explicitly selected development
adapter; `auto` prefers configured Bedrock, then Modal, then the offline
provider.

Use the standard AWS credential chain rather than committing credentials. The
Bedrock proof also defaults to a zero-request preflight. A real proof requires
the explicit provider setting, region, Claude model/inference-profile ID, and
`--execute`; each selected operation runs exactly once with SDK retries and
fallback disabled, then the process exits:

```powershell
tools/uv/uv.exe run python scripts/check_bedrock.py
tools/uv/uv.exe run python scripts/check_bedrock.py --execute rumor dialogue autonomous
```

Embeddings likewise default to `HEARSAY_EMBEDDING_PROVIDER=auto`. The API loads
`BAAI/bge-small-en-v1.5` on CPU, caches it under `.cache/huggingface`, stores
normalized 384-dimensional memory vectors, and adds the upstream retrieval
instruction to recall queries. Set the provider to `fallback` for an explicitly
offline deterministic runtime. See `THIRD_PARTY_MODELS.md` for license and
reproducibility details.

## Current playable slice

The default `hackathon_small` loop is intentionally small but end to end:

1. Marta intercepts the newcomer and asks for a shipment promise.
2. The player walks north-east through the rendered town to confront Bram.
3. Bram offers four clearly labeled approaches. Pip's mutated version then
   appears as an in-world rumor with speaker, listener, and hop.
4. The player settles the shipment, returns to Marta, and sees her recall the
   durable promise outcome.
5. A storm crowds residents into the inn, where Talia presents the next moral
   choice without opening a side-story dashboard.
6. The gold marker leads to Rhea. Candidacy, ballot custody, and the final
   witnessed-count decision resolve into a readable `14–6` election result.

The focused release renders no action bar or always-open ledger. One objective,
one gold target, proximity interaction, a circular minimap, and optional
journal carry the whole run. The broader `full` profile remains available for
the authored regression stories at `/?release_profile=full`; its save is kept
separate and cannot replace the playable-town save on the default URL. The
current memory slice
persists immutable belief lineage and performs holder-scoped 384-dimensional
vector recall with relational reranking. Structured Bedrock/Modal inference is
validated and provenance-tracked. In the small release, Pip's bounded
autonomous decision selects an eligible real memory recipient and exposes its
provider provenance in the town feed. Conflicting claims are stored as independent
inputs and deterministically resolved without losing either source history; a
real Cockroach serialization race proves one coherent active belief survives.
Local BGE embeddings now power configured development recall. Memory-driven
dialogue records and displays the exact belief versions behind an NPC response,
including contested status and provider provenance. Broader relationship
treatment now changes visible standing and unlocks memory-conditioned follow-up
chips through idempotent trust floors/ceilings. The Town Historian now returns a
durably audited lineage response, invokes only the allowlisted Managed MCP
`select_query` tool when separately authenticated, and makes direct fallback
state impossible to mistake for sponsor proof.
Timed promises now resolve into observed outcomes: keeping Marta's word produces
Reliable/Generous traits and grateful endorsement dialogue, while missing the
deadline produces Dishonest/Troublemaker traits and a durable public retelling.
All 20 Greyhaven residents now participate in a deterministic midnight election.
The seeded kept-promise path wins `11–9`; a `10–10` tie remains with Rhea. Every
vote and decisive input is durable in CockroachDB, and the ending panel cites
the exact belief version where memory changed a vote.
Each Bram approach now produces its own public event, relationship change,
semantic rumor, and election weight. Threatening him can end with the town
running the player out; lying about Elias's authority can unravel into the
Exposed ending, both through ordinary three-day play rather than debug state.
On each gossip tick with a new salient Pip account, 2–4 co-located ambient
residents now repeat it in their authored blunt, skeptical, cautious, wry,
practical, precise, or urgent style. Their on-scene bubbles name the
Pip→listener pair; CockroachDB stores every belief and transmission edge;
shallow recall and voting use at most their last three memories with hop/style
attenuation.
Those residents also follow validated three-day,
morning/afternoon/evening/night routines. Consequential actions advance the
authoritative clock, move NPCs on the 2D town map, append a public schedule-shift
event, and persist the same locations that reappear after refresh from the
configured Cockroach Cloud `hearsay` database.
Day 1 evening now draws the GDD's never-cut storm as durable game state. Rain,
screen treatment, and thunder provide the render layer; every
resident evacuates to the inn for the behavior layer; Marta, Nessa, and Pip
react in dialogue. Refresh restores the same storm and crowd, while Day 2 writes
the clear event and resumes ordinary routes.
Day 2 afternoon now stages Bram and Nessa's public argument: the whole town
forms a ring in the square, both faction relationships deteriorate, and three
Town Ledger actions let the player back Bram, defend Nessa, or calm the crowd.
The chosen intervention changes visible standing and traits, becomes immutable
memory for Bram/Nessa/Pip, survives refresh, and appears as exact election
evidence.
Nessa now has a complete post-storm favor: carry her dated harbor log to Elias,
use it to correct Pip's blame story, then ask for the harbor endorsement. The
ledger, Reliable/Influential traits, principal standings, five voter memories,
three transmission edges, endorsement, refresh state, and Landslide ending all
derive from those normal actions and persist in CockroachDB.
A declared candidate may also address the square once per game day. The speech
derives Influential and writes Pip's exact skeptical memory before proximity
echoes carry it onward. An unsupported candidacy reaches Humiliation, while the
speech-only path resolves `10–10` in Rhea's favor as an audited Narrow loss.

## Authority

- `docs/Hearsay_Game_Design_Document.md` governs the game and player experience.
- `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs CockroachDB, AWS,
  memory proof, benchmarking, MCP Historian, and submission compliance.
- `docs/IMPLEMENTATION_PLAN.md` is the implementation queue.
- `docs/IMPLEMENTATION_STATUS.md` records completed gates and the next slice.
- `THIRD_PARTY_ASSETS.md` records the reusable visual assets and their terms.
- `THIRD_PARTY_MODELS.md` records the local embedding model, license, and
  reproducibility details.
