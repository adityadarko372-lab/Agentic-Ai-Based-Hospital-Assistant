import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { mockApi, renderApp, resetSession, signInBeforeRender } from "./renderWithProviders";

describe("Nova Health app shell (signed in)", () => {
  beforeEach(() => {
    resetSession();
    signInBeforeRender();
  });

  it("renders the dashboard with brand, personal greeting and demo notice", async () => {
    mockApi();
    renderApp("/");

    expect(await screen.findByRole("heading", { level: 1, name: /asha/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /nova health, go to dashboard/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("note", { name: /demonstration data notice/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open the ai assistant/i })).toBeInTheDocument();
  });

  it("shows 'Backend connected' when /api/health responds", async () => {
    const { spy } = mockApi();
    renderApp("/");

    expect((await screen.findAllByText("Backend connected")).length).toBeGreaterThan(0);
    expect(spy).toHaveBeenCalledWith("/api/health", expect.objectContaining({ method: "GET" }));
  });

  it("shows 'Backend offline' honestly when the health check fails", async () => {
    mockApi({ healthOnline: false });
    renderApp("/");

    expect((await screen.findAllByText("Backend offline")).length).toBeGreaterThan(0);
    expect(screen.getByText(/unable to reach the nova health server/i)).toBeInTheDocument();
  });

  it("lists every required module in the main navigation", async () => {
    mockApi();
    renderApp("/");

    const sidebar = await screen.findByRole("complementary", { name: /sidebar/i });
    const nav = within(sidebar).getByRole("navigation", { name: "Main" });
    for (const label of ["Dashboard", "AI Assistant", "Symptom Guidance", "Appointments", "Hospital Services", "Agent Activity"]) {
      expect(within(nav).getByRole("link", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });

  it("navigates to a module page and marks the link as current", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/");

    const sidebar = await screen.findByRole("complementary", { name: /sidebar/i });
    await user.click(within(sidebar).getByRole("link", { name: /symptom guidance/i }));

    expect(screen.getByRole("heading", { level: 1, name: "Symptom Guidance" })).toBeInTheDocument();
    expect(within(sidebar).getByRole("link", { name: /symptom guidance/i })).toHaveAttribute("aria-current", "page");
    // Unbuilt modules must say so rather than show fake controls.
    expect(screen.getByText("Not built yet")).toBeInTheDocument();
  });

  it("opens and closes the mobile menu with the keyboard", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/");

    const menuButton = await screen.findByRole("button", { name: /open menu/i });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");

    await user.click(menuButton);
    expect(screen.getByRole("dialog", { name: /main menu/i })).toBeInTheDocument();
    expect(menuButton).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Escape}");
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
  });

  it("shows a helpful not-found page for unknown routes", async () => {
    mockApi();
    renderApp("/no-such-page");

    expect(await screen.findByRole("heading", { level: 1, name: /page not found/i })).toBeInTheDocument();
  });

  it("offers a keyboard skip link to the main content", async () => {
    mockApi();
    renderApp("/");

    expect(await screen.findByRole("link", { name: /skip to main content/i })).toHaveAttribute("href", "#nh-main");
  });
});
