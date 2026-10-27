import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { SESSION_STORAGE_KEY } from "../src/auth/AuthContext";
import { mockApi, renderApp, resetSession, signInBeforeRender } from "./renderWithProviders";

describe("Demo login", () => {
  beforeEach(() => resetSession());

  it("redirects signed-out visitors to the sign-in page", async () => {
    mockApi();
    renderApp("/appointments");

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Appointments" })).not.toBeInTheDocument();
  });

  it("validates empty fields before calling the server", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/login");

    await user.click(await screen.findByRole("button", { name: "Sign in" }));

    expect(screen.getByLabelText(/email/i)).toHaveAccessibleDescription("Please enter your email address.");
    expect(screen.getByLabelText(/password/i)).toHaveAccessibleDescription("Please enter your password.");
    expect(state.calls.some((call) => call.path === "/api/auth/login")).toBe(false);
  });

  it("shows the server's message for a wrong password", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/login");

    await user.type(await screen.findByLabelText(/email/i), "patient@novahealth.demo");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
    expect(window.sessionStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it("signs in with the demo account, returns to the requested page, and signs out", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/appointments");

    await user.click(await screen.findByRole("button", { name: "Fill in" }));
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Appointments" })).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_STORAGE_KEY)).toBe("test-token");
    expect(screen.getByText("Asha Verma", { selector: ".nh-user-menu__name" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it("restores a stored session after a refresh", async () => {
    mockApi();
    signInBeforeRender();
    renderApp("/");

    expect(await screen.findByRole("heading", { level: 1, name: /asha/i })).toBeInTheDocument();
  });
});
