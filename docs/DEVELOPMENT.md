# Hearsay development guide

This guide contains the setup, integration, replay, and verification details
kept out of the project landing page.

## Local setup

Hearsay is pinned to Node.js 22 and pnpm 11.9.0. On Windows, activate the exact
package-manager version once:

```powershell
corepack install --global pnpm@11.9.0
pnpm --version
```

Then bootstrap and run the production-style local application:

```powershell
pnpm bootstrap
pnpm doctor
pnpm play
```

If another pnpm installation shadows Corepack, use the pinned launcher:

```powershell
corepack pnpm@11.9.0 play
```

Open `http://localhost:3000`. The API health endpoint and OpenAPI documentation
are available at `http://localhost:8000/health` and
`http://localhost:8000/docs`.

Use `pnpm dev` while editing. The `pnpm play` command creates a bounded
production build and cleans up the web and API processes it starts.

## Controls

1. Select **Take the road to Greyhaven**.
2. Walk with **WASD** or the **arrow keys**.
3. Press **T**, **Enter**, or **Space** near a resident.
4. Follow the objective card or press **J** to open the journal.

Movement and exploration are free. Consequential conversations advance the
three-day campaign. Refreshing restores the current run from the configured
persistence backend.

## Replay site

The browser-only showcase at `/replay` reconstructs completed deterministic
sessions inside the Greyhaven renderer. Playback uses frozen `RunSnapshot`
sequences rather than video and does not contact the API, CockroachDB, or AWS.

Regenerate checked-in replay bundles after simulation changes:

```powershell
corepack pnpm@11.9.0 replay:export
```

Build the replay-only static artifact:

```powershell
corepack pnpm@11.9.0 replay:build
```

The artifact is staged under the ignored `apps/web/dist` directory.

## CockroachDB Cloud

Put either `DATABASE_URL` or the exported Cockroach Cloud connection values in
the ignored `.env`, then select the durable backend:

```dotenv
HEARSAY_PERSISTENCE_BACKEND=cockroachdb
```

Apply migrations and run the isolated database checks:

```powershell
corepack pnpm@11.9.0 db:migrate
corepack pnpm@11.9.0 db:test
```

Integration tests create and clear only `hearsay_test`; the application uses
`hearsay`. A local Docker database is not required. Select
`HEARSAY_PERSISTENCE_BACKEND=memory` only for the explicit deterministic
development fixture.

## Town Historian and Managed MCP

The Town Historian uses a separate server-side CockroachDB Cloud Managed MCP
credential:

```dotenv
HEARSAY_HISTORIAN_PROVIDER=managed_mcp
COCKROACH_MCP_CLUSTER_ID=your-cluster-id
COCKROACH_MCP_API_KEY=your-independent-api-key
```

The server connects to `https://cockroachlabs.cloud/mcp`, verifies the
advertised `select_query` schema, and permits only a fixed read-only lineage
query. The browser cannot provide SQL or select an MCP tool. Direct-database
fallback responses are labeled `sponsor_proof=false`.

Run the zero-request configuration check or the explicit one-shot proof:

```powershell
tools/uv/uv.exe run python scripts/check_historian.py
tools/uv/uv.exe run python scripts/check_historian.py --execute --trace-fixture
```

## Amazon Bedrock

Local inference defaults to a deterministic provider and cannot accidentally
invoke a paid model. Configure the deployed Bedrock path explicitly:

```dotenv
HEARSAY_LLM_PROVIDER=bedrock
AWS_REGION=your-region
HEARSAY_BEDROCK_MODEL=your-claude-model-or-inference-profile
```

Bedrock uses the Converse API with schema-constrained responses, bounded
retries, and validated fallbacks. Provider, model, latency, attempts, fallback
state, and token usage are stored with inference provenance when available.

Use the standard AWS credential chain. The proof script makes no request unless
`--execute` is supplied:

```powershell
tools/uv/uv.exe run python scripts/check_bedrock.py
tools/uv/uv.exe run python scripts/check_bedrock.py --execute rumor dialogue autonomous
```

## Embeddings

`HEARSAY_EMBEDDING_PROVIDER=auto` loads `BAAI/bge-small-en-v1.5` on CPU and
stores normalized 384-dimensional memory vectors. Weights are cached under the
ignored `.cache/huggingface` directory. Use `fallback` for the explicit offline
deterministic embedding provider. Licensing and reproducibility details are in
[`THIRD_PARTY_MODELS.md`](../THIRD_PARTY_MODELS.md).

## Focused verification

Run the release-path browser check:

```powershell
corepack pnpm@11.9.0 test:e2e:release
```

Run broader checks only when the affected behavior requires them:

```powershell
pnpm test
pnpm typecheck
pnpm lint
```

The testing scripts use isolated services and clean up the processes they own.
