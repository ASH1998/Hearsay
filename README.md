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

Cloud credentials are optional. With
`HEARSAY_PERSISTENCE_BACKEND=memory`, the API uses an explicit deterministic
development fallback; it never silently switches authoritative state.

Inference defaults to `HEARSAY_LLM_PROVIDER=auto`: when the Modal URL and both
tokens are present in `.env`, development uses the configured
`thinkingmachines/Inkling-NVFP4` endpoint. Without them it uses a deterministic
offline provider. Invalid or timed-out responses are schema-rejected, retried,
and replaced with a content-safe fallback whose provider/model provenance is
stored with the transmission.

## Current playable slice

The opening loop is intentionally small but end to end:

1. Start or restore a run.
2. Promise Marta that you will release the inn shipment.
3. Confront Bram about his price.
4. After the second consequential action, Pip visibly repeats a distorted
   version and the authoritative action clock advances.
5. Open “Trace Pip’s rumor” in the Town Ledger to inspect Bram’s source belief,
   Pip’s immutable retelling, and the recorded mutation.

Movement, eavesdropping, and the notice board are free actions. Walk through
connected waypoints with the on-screen controls or WASD/arrow keys. Refreshing
the browser restores the current run from CockroachDB. The current memory slice
persists immutable belief lineage and performs holder-scoped 384-dimensional
vector recall with relational reranking. Structured Modal rumor retelling is
validated and provenance-tracked. Conflicting claims are stored as independent
inputs and deterministically resolved without losing either source history; a
real Cockroach serialization race proves one coherent active belief survives.
Real local embeddings, memory-driven dialogue, and the Managed MCP Historian are
next.

## Authority

- `docs/Hearsay_Game_Design_Document.md` governs the game and player experience.
- `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs CockroachDB, AWS,
  memory proof, benchmarking, MCP Historian, and submission compliance.
- `docs/IMPLEMENTATION_PLAN.md` is the implementation queue.
- `docs/IMPLEMENTATION_STATUS.md` records completed gates and the next slice.
