import { expect, test } from "@playwright/test";

import { openNav, SCREENSHOT_DIR, signIn } from "./helpers";

/**
 * App-shell browser checks against the running app (real backend):
 * - sign-in is required and works
 * - the live backend connection is shown
 * - no horizontal overflow at desktop or phone widths
 * - navigation works with the sidebar (desktop) or drawer (mobile)
 */

test("signed-out visitors see the sign-in page", async ({ page }, testInfo) => {
  await page.goto("/appointments");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.screenshot({ path: `${SCREENSHOT_DIR}/phase2-login-${testInfo.project.name}.png`, fullPage: true });
});

test("wrong password is refused with a clear message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("patient@novahealth.demo");
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText(/incorrect email or password/i);
});

test("dashboard greets the patient and shows the live backend connection", async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole("heading", { level: 1, name: /asha/i })).toBeVisible();
  // Status text lives in a live region on every viewport (visually hidden on phones).
  await expect(page.locator(".nh-topbar").getByRole("status")).toHaveText("Backend connected");
  await expect(page.getByRole("note", { name: /demonstration data notice/i })).toBeVisible();
  // Departments are loaded from the backend directory.
  await expect(page.getByText("Block B, First Floor")).toBeVisible();
});

test("layout has no horizontal overflow", async ({ page }) => {
  await signIn(page);
  for (const path of ["/", "/services", "/design-system", "/appointments"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `horizontal overflow on ${path}`).toBeLessThanOrEqual(0);
  }
});

test("navigation reaches every module page", async ({ page }, testInfo) => {
  await signIn(page);
  const isMobile = testInfo.project.name === "mobile";

  for (const [label, heading] of [
    ["AI Assistant", "AI Assistant"],
    ["Symptom Guidance", "Symptom Guidance"],
    ["Appointments", "Appointments"],
    ["Hospital Services", "Departments"],
    ["Agent Activity", "Agent Activity"],
  ] as const) {
    await openNav(page, isMobile, new RegExp(label, "i"));
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  }
});

test("services page shows the directory from the backend", async ({ page }, testInfo) => {
  await signIn(page, "/services");
  await expect(page.getByRole("heading", { name: "Clinical departments" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Emergency Department" })).toBeVisible();
  await page.screenshot({ path: `${SCREENSHOT_DIR}/phase2-services-${testInfo.project.name}.png`, fullPage: true });
});
