import { defineConfig } from "@playwright/test";

// three gateways on the built page: normal, admin + dev data, and one whose local model is unreachable
const gateway = (port: number, env: Record<string, string> = {}) => ({
  command: `uv run --frozen python web/e2e/server.py ${port}`,
  cwd: "..",
  url: `http://127.0.0.1:${port}/api/meta`,
  timeout: 120_000,
  env: { ...(process.env as Record<string, string>), ...env },
});

export default defineConfig({
  testDir: "e2e",
  timeout: 180_000,
  expect: { timeout: 90_000 },
  workers: 1,  // one local model on one GPU: tests take turns
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:8101", viewport: { width: 1600, height: 1000 }, trace: "retain-on-failure" },
  webServer: [gateway(8101), gateway(8102, { CHAPERONE_ADMIN: "1", CHAPERONE_DEV: "1" }), gateway(8103, { OLLAMA_URL: "http://127.0.0.1:9" })],
});
