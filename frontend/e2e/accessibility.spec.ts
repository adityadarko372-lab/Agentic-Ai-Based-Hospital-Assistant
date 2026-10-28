import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { signIn } from "./helpers";

/**
 * Automated accessibility check (axe-core, WCAG 2.0/2.1 A and AA rules) on
 * every page, including pages with results on screen. Serious and critical
 * problems fail the test. Automated tools find only part of all accessibility
 * issues; this is not a full audit.
 */

// Check the settled screen, not text half-way through a fade-in animation.
test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

async function expectNoSeriousViolations(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const summary = serious.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(" | ")}`);
  expect(summary, `${label}: ${summary.join("\n")}`).toEqual([]);
}

test("login page", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expectNoSeriousViolations(page, "login");
});

test("every signed-in page, with content on screen", async ({ page }) => {
  await signIn(page, "/");
  await page.waitForLoadState("networkidle");
  await expectNoSeriousViolations(page, "dashboard");

  for (const path of ["/services", "/appointments", "/activity", "/design-system"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await expectNoSeriousViolations(page, path);
  }

  await page.goto("/assistant");
  const input = page.getByLabel("Message the assistant");
  await input.fill("What should I bring to my appointment?");
  await input.press("Enter");
  await expect(page.getByRole("list", { name: "Agent steps" })).toBeVisible();
  await input.fill("I have chest pain");
  await input.press("Enter");
  await expect(page.getByRole("alert").filter({ hasText: "Get emergency help now" })).toBeVisible();
  await expectNoSeriousViolations(page, "assistant");

  await page.goto("/symptom-guidance");
  await page.getByRole("checkbox", { name: "Cough", exact: true }).check();
  await page.getByRole("radio", { name: "1 to 3 days" }).check();
  await page.getByRole("radio", { name: /^Mild/ }).check();
  await page.getByRole("button", { name: "Get guidance" }).click();
  await expect(page.getByRole("region", { name: "Your guidance" })).toContainText("General self-care information");
  await expectNoSeriousViolations(page, "symptom-guidance");
});
