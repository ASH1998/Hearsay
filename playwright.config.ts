import { defineConfig } from "@playwright/test";

const apiCommand =
  process.platform === "win32"
    ? ".\\tools\\uv\\uv.exe run uvicorn hearsay_api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000"
    : "./tools/uv/uv run uvicorn hearsay_api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    channel:
      process.env.PLAYWRIGHT_CHANNEL ??
      (process.platform === "win32" ? "chrome" : undefined),
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: apiCommand,
      env: {
        ...process.env,
        HEARSAY_ENV: "test",
        HEARSAY_LLM_PROVIDER: "fallback",
        HEARSAY_PERSISTENCE_BACKEND: "memory",
        HEARSAY_WEB_ORIGIN: "http://localhost:3000",
      },
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command:
        "node apps/web/node_modules/next/dist/bin/next dev apps/web --webpack",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
      },
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
