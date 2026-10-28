import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { canAccessPath, homeForRole } from "../src/config/navigation";
import { DEMO_ACCOUNTS } from "../src/pages/LoginPage";
import {
  makeAppointment,
  makeFrontDeskRequest,
  mockApi,
  renderApp,
  resetSession,
  signInBeforeRender,
  STAFF_TOKEN,
} from "./renderWithProviders";

describe("Demo accounts and role routing (Phase 5)", () => {
  beforeEach(() => resetSession());

  it("lists the project-team demo patients and the staff account", () => {
    const names = DEMO_ACCOUNTS.map((account) => account.name);
    expect(names).toEqual(expect.arrayContaining(["Aditya Singh", "Aaryan Naik", "Bhavish Keni", "Meera Desai"]));
    expect(DEMO_ACCOUNTS.filter((account) => account.role === "front_desk")).toHaveLength(1);
  });

  it("keeps each role on its own pages", () => {
    expect(homeForRole("front_desk")).toBe("/front-desk");
    expect(homeForRole("patient")).toBe("/");
    expect(canAccessPath("patient", "/front-desk")).toBe(false);
    expect(canAccessPath("front_desk", "/appointments")).toBe(false);
    expect(canAccessPath("front_desk", "/services")).toBe(true);
    expect(canAccessPath("patient", "/appointments?department=cardiology")).toBe(true);
  });

  it("fills in the chosen demo account and sends staff to the front desk", async () => {
    mockApi({ frontDeskEnabled: true });
    const user = userEvent.setup();
    renderApp("/login");

    await user.selectOptions(await screen.findByLabelText("Demo account"), "frontdesk@novahealth.demo");
    await user.click(screen.getByRole("button", { name: "Fill in" }));
    expect(screen.getByLabelText(/email/i)).toHaveValue("frontdesk@novahealth.demo");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Front desk" })).toBeInTheDocument();
    expect(screen.getByText("Front desk staff")).toBeInTheDocument();
    // Staff navigation only; the patient assistant button is hidden.
    const sidebar = screen.getByRole("complementary", { name: "Sidebar" });
    expect(within(sidebar).queryByRole("link", { name: /appointments/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /open the ai assistant/i })).not.toBeInTheDocument();
  });

  it("redirects staff away from patient pages and patients away from the front desk", async () => {
    mockApi({ frontDeskEnabled: true });
    signInBeforeRender(STAFF_TOKEN);
    const { unmount } = renderApp("/appointments");
    expect(await screen.findByRole("heading", { level: 1, name: "Front desk" })).toBeInTheDocument();
    unmount();

    resetSession();
    mockApi({ frontDeskEnabled: true });
    signInBeforeRender();
    renderApp("/front-desk");
    expect(await screen.findByRole("heading", { level: 1, name: /asha/i })).toBeInTheDocument();
  });
});

describe("Front desk page", () => {
  beforeEach(() => resetSession());

  it("explains when the feature is switched off on the server", async () => {
    mockApi({ frontDeskEnabled: false });
    signInBeforeRender(STAFF_TOKEN);
    renderApp("/front-desk");

    expect(await screen.findByText("Front-desk review is switched off")).toBeInTheDocument();
    expect(screen.getByText(/FRONT_DESK_ENABLED=true/)).toBeInTheDocument();
  });

  it("confirms a pending request with an optional note", async () => {
    const { state } = mockApi({
      frontDeskEnabled: true,
      frontDeskRequests: [makeFrontDeskRequest({ reference: "NH-APT-0004", patient_name: "Aditya Singh", patient_email: "aditya.singh@novahealth.demo" })],
    });
    const user = userEvent.setup();
    signInBeforeRender(STAFF_TOKEN);
    renderApp("/front-desk");

    const list = await screen.findByRole("list", { name: "Requests to review" });
    expect(within(list).getByText(/aditya\.singh@novahealth\.demo/)).toBeInTheDocument();
    await user.click(within(list).getByRole("button", { name: "Confirm request NH-APT-0004" }));

    const dialog = await screen.findByRole("dialog", { name: "Confirm NH-APT-0004?" });
    await user.type(within(dialog).getByLabelText(/note for the patient/i), "Please arrive 15 minutes early.");
    await user.click(within(dialog).getByRole("button", { name: "Confirm request" }));

    expect(await screen.findByText("No requests waiting for review")).toBeInTheDocument();
    const post = state.calls.find((call) => call.method === "POST" && call.path.endsWith("/decision"))!;
    expect(post.body).toEqual({ decision: "confirm", note: "Please arrive 15 minutes early." });

    await user.click(screen.getByRole("button", { name: "Confirmed" }));
    const confirmed = await screen.findByRole("list", { name: "Requests to review" });
    expect(within(confirmed).getByText("Confirmed")).toBeInTheDocument();
    expect(within(confirmed).getByText(/by Meera Desai/)).toBeInTheDocument();
    expect(within(confirmed).getByText("Note: Please arrive 15 minutes early.")).toBeInTheDocument();
  });

  it("requires a reason before declining", async () => {
    const { state } = mockApi({ frontDeskEnabled: true, frontDeskRequests: [makeFrontDeskRequest()] });
    const user = userEvent.setup();
    signInBeforeRender(STAFF_TOKEN);
    renderApp("/front-desk");

    await user.click(await screen.findByRole("button", { name: "Decline request NH-APT-0001" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Decline request" }));

    expect(within(dialog).getByLabelText(/reason for the patient/i)).toHaveAccessibleDescription(
      "Please add a short note for the patient explaining why.",
    );
    expect(state.calls.some((call) => call.path.endsWith("/decision"))).toBe(false);

    await user.type(within(dialog).getByLabelText(/reason for the patient/i), "No OPD slots that day.");
    await user.click(within(dialog).getByRole("button", { name: "Decline request" }));
    expect(await screen.findByText("No requests waiting for review")).toBeInTheDocument();
    expect(state.frontDesk[0].status).toBe("declined");
  });
});

describe("Patient view of a reviewed request", () => {
  beforeEach(() => resetSession());

  it("shows the real status, reviewer and front-desk note", async () => {
    mockApi({
      appointments: [
        makeAppointment({
          status: "declined",
          reviewed_by: "Meera Desai",
          reviewed_at: new Date().toISOString(),
          review_note: "No OPD slots that day.",
        }),
      ],
    });
    signInBeforeRender();
    renderApp("/appointments");

    const list = await screen.findByRole("list", { name: /your appointment requests/i });
    expect(within(list).getByText("Declined")).toBeInTheDocument();
    expect(within(list).getByText(/reviewed by meera desai/i)).toBeInTheDocument();
    expect(within(list).getByText("Front desk note: No OPD slots that day.")).toBeInTheDocument();
    expect(within(list).queryByRole("button", { name: /cancel request/i })).not.toBeInTheDocument();
  });
});
