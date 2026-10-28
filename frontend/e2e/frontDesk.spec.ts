import { expect, test, type APIRequestContext } from "@playwright/test";

import { indiaDatePlus, SCREENSHOT_DIR, signIn } from "./helpers";

/**
 * Phase 5 (optional) front-desk review, against the real backend.
 * Which test runs depends on FRONT_DESK_ENABLED on the running server, so the
 * suite passes with the feature switched off and with it switched on.
 */
async function frontDeskEnabled(request: APIRequestContext): Promise<boolean> {
  const health = await (await request.get("/api/health")).json();
  return Boolean(health.features?.front_desk_enabled);
}

test("staff see a clear message when front-desk review is switched off", async ({ page, request }) => {
  test.skip(await frontDeskEnabled(request), "FRONT_DESK_ENABLED is on for this server.");
  await signIn(page, "/", "frontdesk@novahealth.demo");
  await expect(page.getByRole("heading", { level: 1, name: "Front desk" })).toBeVisible();
  await expect(page.getByText("Front-desk review is switched off")).toBeVisible();
});

test("a patient request is confirmed by the front desk and the patient sees it", async ({ page, request }, testInfo) => {
  test.skip(!(await frontDeskEnabled(request)), "FRONT_DESK_ENABLED is off for this server.");

  // 1. Bhavish Keni (demo patient) submits a request.
  await signIn(page, "/appointments", "bhavish.keni@novahealth.demo");
  await page.getByRole("combobox", { name: /department/i }).selectOption("general-medicine");
  await page.getByLabel(/preferred date/i).fill(indiaDatePlus(12));
  await page.getByLabel(/reason for appointment/i).fill(`Annual health check (${testInfo.project.name} front-desk e2e).`);
  await page.getByRole("button", { name: "Review request" }).click();
  await page.getByRole("dialog", { name: /submit this appointment request/i }).getByRole("button", { name: "Submit request" }).click();
  const callout = page.getByText(/Request NH-APT-\d{4} submitted\. Status: Pending/);
  await expect(callout).toBeVisible();
  const reference = (await callout.textContent())!.match(/NH-APT-\d{4}/)![0];
  await page.getByRole("button", { name: "Sign out" }).click();

  // 2. Meera Desai (front desk) confirms it with a note.
  await signIn(page, "/", "frontdesk@novahealth.demo");
  await expect(page.getByRole("heading", { level: 1, name: "Front desk" })).toBeVisible();
  const row = page.getByRole("list", { name: "Requests to review" }).getByRole("listitem").filter({ hasText: reference });
  await expect(row).toContainText("bhavish.keni@novahealth.demo");
  await row.getByRole("button", { name: `Confirm request ${reference}` }).click();
  const dialog = page.getByRole("dialog", { name: `Confirm ${reference}?` });
  await dialog.getByLabel(/note for the patient/i).fill("Please arrive 15 minutes early with a photo ID.");
  await dialog.getByRole("button", { name: "Confirm request" }).click();
  await expect(row).toHaveCount(0);

  // A second decision on the same request is refused by the server.
  const token = await page.evaluate(() => window.sessionStorage.getItem("nova_health_session"));
  const again = await request.post(`/api/front-desk/requests/${reference}/decision`, {
    data: { decision: "decline", note: "Trying twice" },
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(again.status()).toBe(409);

  await page.getByRole("button", { name: "Confirmed", exact: true }).click();
  await expect(
    page.getByRole("list", { name: "Requests to review" }).getByRole("listitem").filter({ hasText: reference }),
  ).toContainText("Confirmed by Meera Desai");
  await page.screenshot({ path: `${SCREENSHOT_DIR}/phase5-front-desk-${testInfo.project.name}.png`, fullPage: true });
  await page.getByRole("button", { name: "Sign out" }).click();

  // 3. The patient sees the real status and the note.
  await signIn(page, "/appointments", "bhavish.keni@novahealth.demo");
  const item = page.getByRole("list", { name: /your appointment requests/i }).getByRole("listitem").filter({ hasText: reference });
  await expect(item).toContainText("Confirmed");
  await expect(item).toContainText("Reviewed by Meera Desai");
  await expect(item).toContainText("Please arrive 15 minutes early with a photo ID.");
  await expect(item.getByRole("button", { name: /cancel request/i })).toHaveCount(0);
});

test("staff cannot open patient pages", async ({ page }) => {
  await signIn(page, "/", "frontdesk@novahealth.demo");
  await page.goto("/assistant");
  await expect(page.getByRole("heading", { level: 1, name: "Front desk" })).toBeVisible();
  await expect(page.getByRole("link", { name: /open the ai assistant/i })).toHaveCount(0);
});
