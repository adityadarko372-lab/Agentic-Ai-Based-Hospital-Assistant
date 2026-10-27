import { expect, test } from "@playwright/test";

import { indiaDatePlus, SCREENSHOT_DIR, signIn } from "./helpers";

/**
 * Module 5 end to end, against the real FastAPI + SQLite backend:
 * submit → confirm → saved as Pending with a reference → still there after
 * a page reload → visible on the dashboard → can be cancelled.
 */
test("a patient submits an appointment request and it is saved as Pending", async ({ page }, testInfo) => {
  await signIn(page, "/appointments");
  await expect(page.getByRole("heading", { level: 1, name: "Appointments" })).toBeVisible();

  // Invalid submission is stopped on the client.
  await page.getByRole("button", { name: "Review request" }).click();
  await expect(page.getByText("Please choose a department.")).toBeVisible();

  await page.getByRole("combobox", { name: /department/i }).selectOption("cardiology");
  await page.getByLabel(/preferred date/i).fill(indiaDatePlus(10));
  const reason = `Follow-up consultation (${testInfo.project.name} e2e run).`;
  await page.getByLabel(/reason for appointment/i).fill(reason);
  await page.getByRole("button", { name: "Review request" }).click();

  const dialog = page.getByRole("dialog", { name: /submit this appointment request/i });
  await expect(dialog).toContainText("Cardiology");
  await expect(dialog).toContainText("not a confirmed appointment");
  await dialog.getByRole("button", { name: "Submit request" }).click();

  const callout = page.getByText(/Request NH-APT-\d{4} submitted\. Status: Pending/);
  await expect(callout).toBeVisible();
  const reference = (await callout.textContent())!.match(/NH-APT-\d{4}/)![0];

  const list = page.getByRole("list", { name: /your appointment requests/i });
  const item = list.getByRole("listitem").filter({ hasText: reference });
  await expect(item).toContainText("Pending");
  await expect(item).toContainText("Not yet confirmed by the hospital.");
  await page.screenshot({ path: `${SCREENSHOT_DIR}/phase2-appointments-${testInfo.project.name}.png`, fullPage: true });

  // Persisted in SQLite: still listed after a full page reload.
  await page.reload();
  await expect(page.getByRole("list", { name: /your appointment requests/i }).getByText(reference)).toBeVisible();

  // Shown on the dashboard as an upcoming request and in recent activity.
  await page.goto("/");
  await expect(page.getByText(new RegExp(`${reference} · preferred`))).toBeVisible();
  await expect(page.locator(".nh-activity-feed").getByText(reference).first()).toBeVisible();
  await page.screenshot({ path: `${SCREENSHOT_DIR}/phase2-dashboard-${testInfo.project.name}.png`, fullPage: true });

  // Cancel it again so repeated runs leave a tidy list.
  await page.goto("/appointments");
  const sameItem = page.getByRole("list", { name: /your appointment requests/i }).getByRole("listitem").filter({ hasText: reference });
  await sameItem.getByRole("button", { name: `Cancel request ${reference}` }).click();
  await page.getByRole("dialog", { name: /cancel this request/i }).getByRole("button", { name: "Cancel request" }).click();
  await expect(sameItem).toContainText("Cancelled");
  await expect(sameItem.getByRole("button", { name: /cancel request/i })).toHaveCount(0);
});
