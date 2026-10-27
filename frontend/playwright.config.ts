import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests run against the real dev servers (backend + Vite).
 * They use the Microsoft Edge already installed on Windows (channel "msedge"),
 * so no extra browser download is needed.
 *
 * Start the app first (scripts\start.ps1), then run: npm.cmd run test:e2e
 */
export default defineConfig({
  testDir: "./e2e",
  // The full demo journey sends six chat messages and visits three pages.
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  // Two browsers at a time: more parallel Edge windows overload one laptop and
  // the single dev server, which produced timeouts unrelated to the app.
  workers: 2,
  reporter: [["list"]],
  outputDir: "./test-results",
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "msedge",
    trace: "off",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Edge"], channel: "msedge", viewport: { width: 1440, height: 1000 } } },
    {
      name: "mobile",
      use: {
        channel: "msedge",
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
