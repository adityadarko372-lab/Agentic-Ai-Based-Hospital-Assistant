import { expect, type Page } from "@playwright/test";

export const SCREENSHOT_DIR = "../docs/screenshots";

/**
 * Signs in through the real login form with a fictional demo account
 * (default: the first account in the picker, Asha Verma).
 */
export async function signIn(page: Page, redirectPath = "/", accountEmail?: string): Promise<void> {
  await page.goto(redirectPath);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  if (accountEmail) await page.getByLabel("Demo account").selectOption(accountEmail);
  await page.getByRole("button", { name: "Fill in" }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

/** Returns a YYYY-MM-DD date `days` from today in India (UTC+05:30). */
export function indiaDatePlus(days: number): string {
  const now = Date.now() + 330 * 60 * 1000 + days * 24 * 60 * 60 * 1000;
  return new Date(now).toISOString().slice(0, 10);
}

export async function openNav(page: Page, isMobile: boolean, label: RegExp): Promise<void> {
  if (isMobile) {
    await page.getByRole("button", { name: /open menu/i }).click();
    const drawer = page.getByRole("dialog", { name: /main menu/i });
    await drawer.getByRole("link", { name: label }).click();
    await expect(drawer).toBeHidden();
  } else {
    await page.getByRole("complementary", { name: "Sidebar" }).getByRole("link", { name: label }).click();
  }
}
