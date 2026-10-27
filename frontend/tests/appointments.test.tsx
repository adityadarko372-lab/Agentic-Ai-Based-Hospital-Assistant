import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { validateAppointmentForm } from "../src/components/appointments/appointmentValidation";
import { addDays, todayInIndia } from "../src/utils/dates";
import {
  DEPARTMENTS,
  makeAppointment,
  mockApi,
  renderApp,
  resetSession,
  signInBeforeRender,
} from "./renderWithProviders";

const TODAY = "2026-10-26";
const VALID = {
  patient_name: "Asha Verma",
  department_id: "cardiology",
  preferred_date: "2026-11-02",
  reason: "Follow-up for palpitations.",
};

describe("validateAppointmentForm (mirrors backend rules)", () => {
  it("accepts a valid request", () => {
    expect(validateAppointmentForm(VALID, DEPARTMENTS, TODAY)).toEqual({});
  });

  it.each([
    [{ preferred_date: TODAY }, "preferred_date", "from tomorrow"],
    [{ preferred_date: "2026-10-01" }, "preferred_date", "from tomorrow"],
    [{ preferred_date: addDays(TODAY, 91) }, "preferred_date", "90 days"],
    [{ preferred_date: "" }, "preferred_date", "preferred date"],
    [{ reason: "pain" }, "reason", "at least 10"],
    [{ patient_name: "A" }, "patient_name", "full name"],
    [{ patient_name: "Asha 123" }, "patient_name", "letters"],
    [{ patient_name: "Asha--Verma" }, "patient_name", "letters"],
    [{ patient_name: "<b>Asha</b>" }, "patient_name", "letters"],
    [{ department_id: "" }, "department_id", "choose a department"],
    [{ department_id: "emergency" }, "department_id", "does not take appointment"],
  ])("rejects %o", (override, field, fragment) => {
    const errors = validateAppointmentForm({ ...VALID, ...override }, DEPARTMENTS, TODAY);
    expect(errors[field as keyof typeof errors]).toContain(fragment);
  });

  it("accepts the 90th day and names in Indian scripts", () => {
    expect(validateAppointmentForm({ ...VALID, preferred_date: addDays(TODAY, 90) }, DEPARTMENTS, TODAY)).toEqual({});
    for (const name of ["आशा वर्मा", "Dr. K. Iyer", "Anne-Marie D'Souza", "கவியா ஐயர்"]) {
      expect(validateAppointmentForm({ ...VALID, patient_name: name }, DEPARTMENTS, TODAY)).toEqual({});
    }
  });
});

describe("Appointments page", () => {
  beforeEach(() => {
    resetSession();
    signInBeforeRender();
  });

  it("shows field errors and does not submit an incomplete form", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/appointments");

    await user.click(await screen.findByRole("button", { name: "Review request" }));

    expect(screen.getByLabelText(/department/i)).toHaveAccessibleDescription("Please choose a department.");
    expect(screen.getByLabelText(/preferred date/i)).toHaveAccessibleDescription("Please choose a preferred date.");
    expect(screen.getByLabelText(/reason for appointment/i)).toHaveAccessibleDescription(/at least 10 characters/);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(state.calls.some((call) => call.method === "POST" && call.path === "/api/appointments")).toBe(false);
  });

  it("only offers departments that take appointment requests", async () => {
    mockApi();
    renderApp("/appointments");

    const select = await screen.findByRole("combobox", { name: /department/i });
    const options = within(select).getAllByRole("option").map((option) => option.textContent);
    expect(options).toContain("Cardiology");
    expect(options).not.toContain("Emergency Department");
  });

  it("submits after confirmation, sends an idempotency key and shows the request as Pending", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/appointments?department=cardiology");

    // Name is prefilled from the signed-in profile; department from the link.
    expect(await screen.findByLabelText(/patient name/i)).toHaveValue("Asha Verma");
    expect(screen.getByLabelText(/department/i)).toHaveValue("cardiology");

    await user.type(screen.getByLabelText(/preferred date/i), addDays(todayInIndia(), 7));
    await user.type(screen.getByLabelText(/reason for appointment/i), "Follow-up for palpitations.");
    await user.click(screen.getByRole("button", { name: "Review request" }));

    const dialog = await screen.findByRole("dialog", { name: /submit this appointment request/i });
    expect(within(dialog).getByText("Cardiology")).toBeInTheDocument();
    expect(within(dialog).getByText(/not a confirmed appointment/i)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Submit request" }));

    expect(await screen.findByText(/Request NH-APT-0001 submitted\. Status: Pending/)).toBeInTheDocument();
    const list = await screen.findByRole("list", { name: /your appointment requests/i });
    expect(within(list).getByText("NH-APT-0001")).toBeInTheDocument();
    expect(within(list).getByText("Pending")).toBeInTheDocument();
    expect(within(list).getByText(/not yet confirmed by the hospital/i)).toBeInTheDocument();

    const post = state.calls.find((call) => call.method === "POST" && call.path === "/api/appointments")!;
    expect(post.headers["Idempotency-Key"]).toMatch(/.{8,}/);
    expect(post.body).toMatchObject({ patient_name: "Asha Verma", department_id: "cardiology" });
  });

  it("shows server-side validation messages next to the fields", async () => {
    mockApi({ createFieldErrors: { preferred_date: "Please choose a date from tomorrow onwards." } });
    const user = userEvent.setup();
    renderApp("/appointments?department=cardiology");

    await user.type(await screen.findByLabelText(/preferred date/i), addDays(todayInIndia(), 3));
    await user.type(screen.getByLabelText(/reason for appointment/i), "Routine heart check-up.");
    await user.click(screen.getByRole("button", { name: "Review request" }));
    await user.click(await screen.findByRole("button", { name: "Submit request" }));

    expect(await screen.findByLabelText(/preferred date/i)).toHaveAccessibleDescription(
      "Please choose a date from tomorrow onwards.",
    );
  });

  it("lists existing requests with honest statuses", async () => {
    mockApi({
      appointments: [
        makeAppointment({ reference: "NH-APT-0002", status: "cancelled", department_name: "General Medicine" }),
        makeAppointment({ reference: "NH-APT-0001" }),
      ],
    });
    renderApp("/appointments");

    const list = await screen.findByRole("list", { name: /your appointment requests/i });
    expect(within(list).getByText("Cancelled")).toBeInTheDocument();
    expect(within(list).getByText("Pending")).toBeInTheDocument();
    // Only pending requests can be cancelled.
    expect(within(list).getAllByRole("button", { name: /cancel request/i })).toHaveLength(1);
  });
});
