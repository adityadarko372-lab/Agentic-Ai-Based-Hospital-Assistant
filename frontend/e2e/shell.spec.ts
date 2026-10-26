import { expect, test } from "@playwright/test";

/**
 * Phase 1 browser checks against the running app:
 * - the real backend is reached through the Vite proxy
 * - no horizontal overflow at desktop or phone widths
 * - navigation works with the sidebar (desktop) or drawer (mobile)
 */

const SCREENSHOT_DIR = "../docs/screenshots";

test("dashboard shows the live backend connection", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /welcome to nova health/i })).toBeVisible();
  // Status text lives in a live region on every viewport (visually hidden on phones).
  await expect(page.locator(".nh-topbar").getByRole("status")).toHaveText("Backend connected");
  await expect(page.getByRole("note", { name: /demonstration data notice/i })).toBeVisible();
});

test("layout has no horizontal overflow", async ({ page }, testInfo) => {
  for (const path of ["/", "/services", "/design-system", "/appointments"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `horizontal overflow on ${path}`).toBeLessThanOrEqual(0);
  }

  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.screenshot({
    path: `${SCREENSHOT_DIR}/phase1-dashboard-${testInfo.project.name}.png`,
    fullPage: true,
  });
});

test("navigation reaches every module page", async ({ page }, testInfo) => {
  await page.goto("/");
  const isMobile = testInfo.project.name === "mobile";

  for (const [label, heading] of [
    ["AI Assistant", "AI Assistant"],
    ["Symptom Guidance", "Symptom Guidance"],
    ["Appointments", "Appointments"],
    ["Hospital Services", "Departments"],
    ["Agent Activity", "Agent Activity"],
  ] as const) {
    if (isMobile) {
      await page.getByRole("button", { name: /open menu/i }).click();
      const drawer = page.getByRole("dialog", { name: /main menu/i });
      await drawer.getByRole("link", { name: new RegExp(label, "i") }).click();
      await expect(drawer).toBeHidden();
    } else {
      await page.getByRole("complementary", { name: "Sidebar" }).getByRole("link", { name: new RegExp(label, "i") }).click();
    }
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  }
});

test("design system page renders for review", async ({ page }, testInfo) => {
  await page.goto("/design-system");
  await expect(page.getByRole("heading", { level: 1, name: /components and states/i })).toBeVisible();
  await page.screenshot({
    path: `${SCREENSHOT_DIR}/phase1-design-system-${testInfo.project.name}.png`,
    fullPage: true,
  });
});
