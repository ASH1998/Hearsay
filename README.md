# Hearsay

**The truth is what survives the telling.**

Hearsay is a browser-based social-memory game set in Greyhaven. You have three
days to win a mayoral election in a town where promises become rumors, rumors
mutate as people repeat them, and every decisive memory keeps its provenance.

The project is under active implementation. The playable foundation provides an
authoritative FastAPI run/action/snapshot loop, durable CockroachDB persistence,
and an optimized React Three Fiber Greyhaven scene with animated characters,
graph-constrained movement, conversation camera focus, and storm presentation.

## Local setup

On Windows:

```powershell
pnpm bootstrap
pnpm doctor
pnpm dev
```

Then open `http://localhost:3000`. The API serves health and OpenAPI
documentation at `http://localhost:8000/health` and
`http://localhost:8000/docs`.

To use Cockroach Cloud on Windows, put either `DATABASE_URL` or the exported
`username`, `password`, `command_to_create_cert`, and `command_to_connect`
values in the ignored `.env`, then enable the durable backend:

```dotenv
HEARSAY_PERSISTENCE_BACKEND=cockroachdb
```

```powershell
pnpm db:migrate
pnpm db:test
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

Cloud credentials are optional. With
`HEARSAY_PERSISTENCE_BACKEND=memory`, the API uses an explicit deterministic
development fallback; it never silently switches authoritative state.

Inference defaults to `HEARSAY_LLM_PROVIDER=auto`: when the Modal URL and both
tokens are present in `.env`, development uses the configured
`thinkingmachines/Inkling-NVFP4` endpoint. Without them it uses a deterministic
offline provider. Invalid or timed-out responses are schema-rejected, retried,
and replaced with a content-safe fallback whose provider/model provenance is
stored with the transmission.

Embeddings likewise default to `HEARSAY_EMBEDDING_PROVIDER=auto`. The API loads
`BAAI/bge-small-en-v1.5` on CPU, caches it under `.cache/huggingface`, stores
normalized 384-dimensional memory vectors, and adds the upstream retrieval
instruction to recall queries. Set the provider to `fallback` for an explicitly
offline deterministic runtime. See `THIRD_PARTY_MODELS.md` for license and
reproducibility details.

## Current playable slice

The opening loop is intentionally small but end to end:

1. Start or restore a run.
2. Promise Marta that you will release the inn shipment.
3. Confront Bram about his price.
4. After the second consequential action, Pip visibly repeats a distorted
   version and the authoritative action clock advances.
5. Open “Trace Pip’s rumor” in the Town Ledger to inspect Bram’s source belief,
   Pip’s immutable retelling, and the recorded mutation.
6. Return to Bram before evening and pay to release Marta's shipment—or let the
   deadline pass. The ledger, notice-board traits, Pip's chatter, Marta's
   treatment, and immutable promise memory all reflect the outcome.
7. Sleep to Day 2, declare against Rhea, and advance to election night. All 20
   residents vote from stored disposition, traits, relationships, and memories;
   the ending shows which exact inputs turned the tally.

Movement, eavesdropping, and the notice board are free actions. Walk through
connected waypoints with the on-screen controls or WASD/arrow keys. Refreshing
the browser restores the current run from CockroachDB. The current memory slice
persists immutable belief lineage and performs holder-scoped 384-dimensional
vector recall with relational reranking. Structured Modal rumor retelling is
validated and provenance-tracked. Conflicting claims are stored as independent
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

## Authority

- `docs/Hearsay_Game_Design_Document.md` governs the game and player experience.
- `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs CockroachDB, AWS,
  memory proof, benchmarking, MCP Historian, and submission compliance.
- `docs/IMPLEMENTATION_PLAN.md` is the implementation queue.
- `docs/IMPLEMENTATION_STATUS.md` records completed gates and the next slice.
- `THIRD_PARTY_MODELS.md` records the local embedding model, license, and
  reproducibility details.
