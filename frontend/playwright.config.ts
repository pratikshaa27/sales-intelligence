import { defineConfig, devices } from "@playwright/test";

// Runs against an already-running stack (docker-compose up, or `npm run dev` + the backend
// running separately) rather than spawning its own servers — this project's stack is
// multi-service (postgres/redis/backend/worker/frontend), which Playwright's single-process
// `webServer` option isn't a good fit for. CI brings the real docker-compose stack up first
// (see .github/workflows/ci.yml's `e2e` job) and points these env vars at it.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // the spec is one long golden-path flow sharing state across steps
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3002",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
