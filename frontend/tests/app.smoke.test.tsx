import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { mockHealthFetch, renderApp } from "./renderWithProviders";

describe("Nova Health app shell", () => {
  it("renders the dashboard with brand, welcome heading and demo notice", async () => {
    mockHealthFetch(true);
    renderApp("/");

    expect(screen.getAllByRole("link", { name: /nova health, go to dashboard/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { level: 1, name: /welcome to nova health/i })).toBeInTheDocument();
    expect(screen.getByRole("note", { name: /demonstration data notice/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open the ai assistant/i })).toBeInTheDocument();
  });

  it("shows 'Backend connected' when /api/health responds", async () => {
    const fetchMock = mockHealthFetch(true);
    renderApp("/");

    expect((await screen.findAllByText("Backend connected")).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith("/api/health", expect.objectContaining({ method: "GET" }));
  });

  it("shows 'Backend offline' honestly when the API is unreachable", async () => {
    mockHealthFetch(false);
    renderApp("/");

    expect((await screen.findAllByText("Backend offline")).length).toBeGreaterThan(0);
    expect(screen.getByText(/unable to reach the nova health server/i)).toBeInTheDocument();
  });

  it("lists every required module in the main navigation", () => {
    mockHealthFetch(true);
    renderApp("/");

    const sidebar = screen.getByRole("complementary", { name: /sidebar/i });
    const nav = within(sidebar).getByRole("navigation", { name: "Main" });
    for (const label of [
      "Dashboard",
      "AI Assistant",
      "Symptom Guidance",
      "Appointments",
      "Hospital Services",
      "Agent Activity",
    ]) {
      expect(within(nav).getByRole("link", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });

  it("navigates to a module page and marks the link as current", async () => {
    mockHealthFetch(true);
    const user = userEvent.setup();
    renderApp("/");

    const sidebar = screen.getByRole("complementary", { name: /sidebar/i });
    await user.click(within(sidebar).getByRole("link", { name: /appointments/i }));

    expect(screen.getByRole("heading", { level: 1, name: "Appointments" })).toBeInTheDocument();
    expect(within(sidebar).getByRole("link", { name: /appointments/i })).toHaveAttribute("aria-current", "page");
    // Unbuilt modules must say so rather than show fake controls.
    expect(screen.getByText("Not built yet")).toBeInTheDocument();
  });

  it("opens and closes the mobile menu with the keyboard", async () => {
    mockHealthFetch(true);
    const user = userEvent.setup();
    renderApp("/");

    const menuButton = screen.getByRole("button", { name: /open menu/i });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");

    await user.click(menuButton);
    expect(screen.getByRole("dialog", { name: /main menu/i })).toBeInTheDocument();
    expect(menuButton).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Escape}");
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
  });

  it("shows a helpful not-found page for unknown routes", () => {
    mockHealthFetch(true);
    renderApp("/no-such-page");

    expect(screen.getByRole("heading", { level: 1, name: /page not found/i })).toBeInTheDocument();
  });

  it("offers a keyboard skip link to the main content", () => {
    mockHealthFetch(true);
    renderApp("/");

    expect(screen.getByRole("link", { name: /skip to main content/i })).toHaveAttribute("href", "#nh-main");
  });
});
