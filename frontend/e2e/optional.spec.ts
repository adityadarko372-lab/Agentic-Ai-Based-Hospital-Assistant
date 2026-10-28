import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { SCREENSHOT_DIR, signIn } from "./helpers";

/**
 * Phase 5 optional assistant features, against the real backend.
 * Each test runs only when the running server reports the feature as on, so
 * this file passes with every flag off and with every flag on.
 */
async function features(request: APIRequestContext) {
  return (await (await request.get("/api/health")).json()).features as Record<string, string | boolean>;
}

async function ask(page: Page, text: string) {
  const input = page.getByLabel("Message the assistant");
  await input.fill(text);
  await input.press("Enter");
}

const lastReply = (page: Page) => page.locator(".nh-message--assistant").last();

test("health information: cited passage, and no guessing when there is no good match", async ({ page, request }, testInfo) => {
  const f = await features(request);
  test.skip(!(f.health_info_enabled && f.health_info_index_present), "Health information is off or its index is not built.");

  await signIn(page, "/assistant");
  await ask(page, "What is glaucoma?");
  await expect(lastReply(page)).toContainText("Health Information Agent", { timeout: 30_000 });
  await expect(lastReply(page)).toContainText("General information");
  await expect(lastReply(page)).toContainText("not medical advice");
  await expect(lastReply(page).getByRole("link", { name: /page \(opens in a new tab\)/ })).toHaveAttribute("href", /^https:\/\//);
  await expect(page.getByRole("list", { name: "Agent steps" })).toContainText("Searched NIH MedQuAD");
  await page.screenshot({ path: `${SCREENSHOT_DIR}/phase5-health-info-${testInfo.project.name}.png`, fullPage: true });

  await ask(page, "What is quantum chromodynamics?");
  await expect(lastReply(page)).toContainText("won't guess");

  // Diagnosis requests are still refused before any retrieval.
  await ask(page, "Do I have diabetes?");
  await expect(lastReply(page)).toContainText("can't diagnose");
});

test("trained classifier: routes a question the rules cannot, and the trace says so", async ({ page, request }) => {
  const f = await features(request);
  test.skip(f.intent_classifier_active !== "transformer", "The trained classifier is not active.");

  await signIn(page, "/assistant");
  // The rules find no strong pattern here; the hybrid hands it to the model.
  await ask(page, "where do i pick up my lab reports");
  await expect(lastReply(page)).toContainText("Patient Assistance Agent", { timeout: 30_000 });
  await expect(page.getByRole("list", { name: "Agent steps" })).toContainText("method: transformer");
});

test("AI rewording: never touches emergency guidance", async ({ page, request }) => {
  const f = await features(request);
  test.skip(!f.llm_phrasing_enabled, "AI rewording is off.");

  await signIn(page, "/assistant");
  await ask(page, "I have severe chest pain");
  const alert = page.getByRole("alert").filter({ hasText: "Get emergency help now" });
  await expect(alert).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("list", { name: "Agent steps" })).toContainText("keep their exact template wording");
});
