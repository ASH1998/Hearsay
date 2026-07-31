import { defineConfig } from "@playwright/test";

const webPort = Number(process.env.HEARSAY_E2E_WEB_PORT ?? "3000");
const apiPort = Number(process.env.HEARSAY_E2E_API_PORT ?? "8000");
const webOrigin = `http://localhost:${webPort}`;
const apiOrigin = `http://localhost:${apiPort}`;
const apiCommand =
  process.platform === "win32"
    ? `.\\tools\\python\\cpython-3.12.13-windows-x86_64-none\\python.exe -m uvicorn hearsay_api.main:app --app-dir apps/api/src --host 127.0.0.1 --port ${apiPort}`
    : `./.venv/bin/python -m uvicorn hearsay_api.main:app --app-dir apps/api/src --host 127.0.0.1 --port ${apiPort}`;

const apiPythonPath =
  process.platform === "win32"
    ? "apps/api/src;.venv/Lib/site-packages"
    : process.env.PYTHONPATH;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: process.env.CI ? 2 : 3,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  timeout: 60_000,
  use: {
    baseURL: webOrigin,
    channel:
      process.env.PLAYWRIGHT_CHANNEL ??
      (process.platform === "win32" ? "chrome" : undefined),
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: process.env.HEARSAY_E2E_EXTERNAL_SERVERS
    ? undefined
    : [
        {
          command: apiCommand,
          env: {
            ...process.env,
            ...(apiPythonPath ? { PYTHONPATH: apiPythonPath } : {}),
            HEARSAY_EMBEDDING_PROVIDER: "fallback",
            HEARSAY_ENV: "test",
            HEARSAY_LLM_PROVIDER: "fallback",
            HEARSAY_PERSISTENCE_BACKEND: "memory",
            HEARSAY_WEB_ORIGIN: webOrigin,
          },
          port: apiPort,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
        {
          command:
            `node apps/web/node_modules/next/dist/bin/next dev apps/web --webpack -p ${webPort}`,
          env: {
            ...process.env,
            NEXT_PUBLIC_API_BASE_URL: apiOrigin,
          },
          port: webPort,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
        },
      ],
});
