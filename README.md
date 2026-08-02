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

## Architecture

![Hearsay NPC memory architecture](docs/assets/hearsay-npc-memory-architecture.png)

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

### Recorded run site

The browser-only showcase at `http://localhost:3000/replay` reconstructs two
completed deterministic sessions inside the real Greyhaven renderer: a 15–5
election victory and a 10–10 loss after the newcomer's earlier choices are
exposed. Playback uses frozen `RunSnapshot` sequences, never an MP4, and offers
play/pause, scene stepping, scrubbing, and speed controls without contacting the
API, CockroachDB, or AWS.

Regenerate and validate the checked-in replay bundles after simulation changes:

```powershell
corepack pnpm@11.9.0 replay:export
```

Produce the replay-only static deployment artifact:

```powershell
corepack pnpm@11.9.0 replay:build
```

The ordinary root URL remains the live local game. The static replay build makes
the run selector the root page and stages the Sites-compatible artifact under
the ignored `apps/web/dist` directory.

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

