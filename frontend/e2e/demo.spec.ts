import { expect, type Page, test } from "@playwright/test";

import { SCREENSHOT_DIR, signIn } from "./helpers";

/**
 * The full demonstration sequence from partial implementation.md, section 5,
 * run against the real FastAPI + SQLite backend. One screenshot per step is
 * saved to docs/screenshots/ for the project report.
 */

async function send(page: Page, text: string) {
  const input = page.getByLabel("Message the assistant");
  await input.fill(text);
  await input.press("Enter");
}

const lastReply = (page: Page) => page.getByRole("log", { name: "Messages" }).locator(".nh-message--assistant").last();

test("examination demo: steps 1 to 6", async ({ page }, testInfo) => {
  const shot = (step: string) =>
    page.screenshot({ path: `${SCREENSHOT_DIR}/demo-${step}-${testInfo.project.name}.png`, fullPage: true });

  // Step 1: open the website and show the patient dashboard.
  await signIn(page, "/");
  await expect(page.getByRole("heading", { level: 1, name: /good (morning|afternoon|evening), asha/i })).toBeVisible();
  await expect(page.getByRole("region", { name: "Quick access" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent activity" })).toBeVisible();
  await shot("step1-dashboard");

  // Step 2: open the assistant and ask a hospital-related question.
  await page.getByRole("link", { name: "Ask the assistant" }).click();
  await page.getByRole("button", { name: "Which department should I visit?" }).click();
  await expect(lastReply(page)).toContainText("Patient Assistance Agent");
  await expect(lastReply(page)).toContainText("General Medicine");
  await shot("step2-hospital-question");

  // Step 3: an appointment request is routed by the Supervisory Agent to the Appointment Agent.
  await send(page, "I want to book an appointment");
  await expect(lastReply(page)).toContainText("Appointment Agent");
  const steps = page.getByRole("list", { name: "Agent steps" });
  await expect(steps).toContainText("Routed to Appointment Agent");
  await shot("step3-routing");

  // Step 4: the Appointment Agent collects the details; the request is saved as Pending.
  await send(page, "Dermatology");
  await send(page, "in 10 days");
  await expect(lastReply(page)).toContainText("reason");
  await send(page, `Itchy rash on both arms (${testInfo.project.name} demo run)`);
  await page.getByRole("button", { name: "Yes, submit it" }).click();
  const saved = lastReply(page).getByText(/Request NH-APT-\d{4} saved\. Status: Pending/);
  await expect(saved).toBeVisible();
  const reference = (await saved.textContent())!.match(/NH-APT-\d{4}/)![0];
  await page.goto("/appointments");
  const item = page.getByRole("list", { name: /your appointment requests/i }).getByRole("listitem").filter({ hasText: reference });
  await expect(item).toContainText("Pending");
  await expect(item).toContainText("Not yet confirmed by the hospital.");
  await shot("step4-pending");

  // Step 5: sample symptoms in the care-navigation module.
  await page.goto("/symptom-guidance");
  await page.getByRole("checkbox", { name: "Cough", exact: true }).check();
  await page.getByRole("radio", { name: "1 to 3 days" }).check();
  await page.getByRole("radio", { name: /^Mild/ }).check();
  await page.getByRole("button", { name: "Get guidance" }).click();
  const guidance = page.getByRole("region", { name: "Your guidance" });
  await expect(guidance).toContainText("General self-care information");
  await expect(guidance).toContainText("not a diagnosis");
  await shot("step5-symptom-guidance");

  // Step 5 (safety): a warning sign gets emergency guidance immediately.
  await page.getByRole("button", { name: "Start again" }).click();
  await page.getByRole("checkbox", { name: "Chest pain or pressure" }).check();
  await expect(page.getByRole("alert").filter({ hasText: "Get emergency help now" })).toBeVisible();
  await page.getByRole("button", { name: "Get guidance" }).click();
  await expect(guidance.getByRole("link", { name: /112/ })).toHaveAttribute("href", "tel:112");
  await shot("step5-emergency");

  // Step 6: the activity history shows which agent handled each request.
  await page.goto("/activity");
  const runs = page.getByRole("list", { name: "Agent runs" });
  for (const agent of ["Patient Assistance", "Appointment", "Care Navigation"]) {
    await expect(runs.getByRole("listitem").filter({ hasText: agent }).first()).toBeVisible();
  }
  await runs.getByRole("button", { name: /symptom form/i }).first().click();
  await expect(page.getByRole("list", { name: "Agent steps" })).toContainText("Received the symptom form");
  await shot("step6-activity");

  // Tidy up so repeated demo runs leave the request list clean.
  await page.goto("/appointments");
  await item.getByRole("button", { name: `Cancel request ${reference}` }).click();
  await page.getByRole("dialog", { name: /cancel this request/i }).getByRole("button", { name: "Cancel request" }).click();
  await expect(item).toContainText("Cancelled");
});
