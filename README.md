# Hearsay

**The truth is what survives the telling.**

Hearsay is a browser-based social-memory game set in Greyhaven. You have three
days to win a mayoral election in a town where promises become rumors, rumors
mutate as people repeat them, and every decisive memory keeps its provenance.

The project is under active implementation. The current vertical slice provides
an authoritative FastAPI run/action/snapshot loop, durable CockroachDB
persistence, and a compact React Three Fiber Greyhaven scene.

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
only `hearsay_test`; the application uses `hearsay`. A disposable Docker Compose
stack remains available as an optional credential-free path.

Cloud credentials are optional. With
`HEARSAY_PERSISTENCE_BACKEND=memory`, the API uses an explicit deterministic
development fallback; it never silently switches authoritative state.

## Current playable slice

The opening loop is intentionally small but end to end:

1. Start or restore a run.
2. Promise Marta that you will release the inn shipment.
3. Confront Bram about his price.
4. After the second consequential action, Pip visibly repeats a distorted
   version and the authoritative action clock advances.

Movement, eavesdropping, and the notice board are free actions. Refreshing the
browser restores the current run from CockroachDB when the durable backend is
enabled. Full belief provenance and vector retrieval are the next data slice.

## Authority

- `docs/Hearsay_Game_Design_Document.md` governs the game and player experience.
- `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs CockroachDB, AWS,
  memory proof, benchmarking, MCP Historian, and submission compliance.
- `docs/IMPLEMENTATION_PLAN.md` is the implementation queue.
- `docs/IMPLEMENTATION_STATUS.md` records completed gates and the next slice.
