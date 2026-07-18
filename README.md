# Hearsay

**The truth is what survives the telling.**

Hearsay is a browser-based social-memory game set in Greyhaven. You have three
days to win a mayoral election in a town where promises become rumors, rumors
mutate as people repeat them, and every decisive memory keeps its provenance.

The project is under active implementation. The current vertical slice provides
an authoritative FastAPI run/action/snapshot loop and a compact React Three
Fiber Greyhaven scene.

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

To run the same slice with a disposable local CockroachDB container:

```powershell
docker compose up --build
```

Cloud credentials are optional for local development. Missing LLM, embedding,
or CockroachDB integrations use explicit deterministic development fallbacks;
they never silently alter authoritative state.

## Current playable slice

The opening loop is intentionally small but end to end:

1. Start or restore a run.
2. Promise Marta that you will release the inn shipment.
3. Confront Bram about his price.
4. After the second consequential action, Pip visibly repeats a distorted
   version and the authoritative action clock advances.

Movement, eavesdropping, and the notice board are free actions. Refreshing the
browser restores the current run from the API process. Durable CockroachDB
persistence and full belief provenance are the next implementation slice.

## Authority

- `docs/Hearsay_Game_Design_Document.md` governs the game and player experience.
- `docs/Hearsay_Hackathon_Blueprint_FINAL_v2.md` governs CockroachDB, AWS,
  memory proof, benchmarking, MCP Historian, and submission compliance.
- `docs/IMPLEMENTATION_PLAN.md` is the implementation queue.
- `docs/IMPLEMENTATION_STATUS.md` records completed gates and the next slice.
