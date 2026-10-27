import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { makeAppointment, mockApi, renderApp, resetSession, signInBeforeRender } from "./renderWithProviders";

describe("Patient dashboard (Module 1)", () => {
  beforeEach(() => {
    resetSession();
    signInBeforeRender();
  });

  it("shows every element the specification lists", async () => {
    mockApi();
    renderApp("/");

    expect(await screen.findByRole("heading", { level: 1, name: /asha/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ask the assistant/i })).toBeInTheDocument();
    const quickAccess = screen.getByRole("region", { name: "Quick access" });
    expect(within(quickAccess).getByRole("link", { name: /symptom guidance/i })).toBeInTheDocument();
    expect(within(quickAccess).getByRole("link", { name: /book appointment/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hospital services" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent activity" })).toBeInTheDocument();
    // Services come from the API.
    expect(await screen.findByText("Block B, First Floor")).toBeInTheDocument();
  });

  it("shows helpful empty states when there is no data yet", async () => {
    mockApi();
    renderApp("/");

    expect(await screen.findByText("No upcoming requests")).toBeInTheDocument();
    expect(await screen.findByText("No activity yet")).toBeInTheDocument();
  });

  it("shows pending upcoming requests and the activity history from the API", async () => {
    mockApi({
      appointments: [
        makeAppointment({ reference: "NH-APT-0007" }),
        makeAppointment({ reference: "NH-APT-0006", status: "cancelled" }),
      ],
      activity: [
        {
          id: 1,
          event_type: "appointment.submitted",
          actor: "You",
          summary: "Appointment request submitted to Cardiology. Status: pending hospital review.",
          reference: "NH-APT-0007",
          created_at: new Date().toISOString(),
        },
      ],
    });
    renderApp("/");

    expect(await screen.findByText(/NH-APT-0007 · preferred/)).toBeInTheDocument();
    // Cancelled requests are not "upcoming".
    expect(screen.queryByText(/NH-APT-0006 · preferred/)).not.toBeInTheDocument();
    expect(await screen.findByText(/submitted to Cardiology/)).toBeInTheDocument();
    expect(screen.getByText("By You")).toBeInTheDocument();
    expect(screen.getByText("just now")).toBeInTheDocument();
  });
});
