import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { mockApi, renderApp, resetSession, signInBeforeRender } from "./renderWithProviders";

describe("Symptom Guidance (Module 4)", () => {
  beforeEach(() => {
    resetSession();
    signInBeforeRender();
  });

  it("asks for symptoms, duration and severity before submitting", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/symptom-guidance");

    await user.click(await screen.findByRole("button", { name: "Get guidance" }));

    expect(screen.getByText("Please select at least one symptom or describe how you feel.")).toBeInTheDocument();
    expect(screen.getByText("Please choose how long you have had the symptoms.")).toBeInTheDocument();
    expect(screen.getByText("Please choose how severe the symptoms are.")).toBeInTheDocument();
    expect(state.calls.some((call) => call.path === "/api/care-navigation/assess")).toBe(false);
  });

  it("shows emergency help as soon as a warning sign is ticked, before submitting", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/symptom-guidance");

    await user.click(await screen.findByRole("checkbox", { name: "Chest pain or pressure" }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Get emergency help now");
    expect(within(alert).getByRole("link", { name: /112/ })).toHaveAttribute("href", "tel:112");
    expect(within(alert).getByRole("link", { name: /108/ })).toHaveAttribute("href", "tel:108");
  });

  it("points self-harm to Tele-MANAS 14416", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/symptom-guidance");

    await user.click(await screen.findByRole("checkbox", { name: /suicide or self-harm/i }));
    expect(within(screen.getByRole("alert")).getByRole("link", { name: /14416/ })).toHaveAttribute("href", "tel:14416");
  });

  it("submits the answers and shows guidance from the Care Navigation Agent", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/symptom-guidance");

    await user.click(await screen.findByRole("checkbox", { name: "Cough" }));
    await user.click(screen.getByRole("radio", { name: "1 to 3 days" }));
    await user.click(screen.getByRole("radio", { name: "Mild" }));
    await user.click(screen.getByRole("button", { name: "Get guidance" }));

    expect(await screen.findByText("General self-care information")).toBeInTheDocument();
    expect(screen.getAllByText("Care Navigation Agent").length).toBeGreaterThan(0);
    expect(screen.getByText(/not a diagnosis/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /request an appointment with general medicine/i })).toHaveAttribute(
      "href",
      "/appointments?department=general-medicine",
    );
    expect(screen.getByRole("heading", { name: "Your guidance" })).toHaveFocus();

    const post = state.calls.find((call) => call.path === "/api/care-navigation/assess")!;
    expect(post.body).toEqual({
      symptom_ids: ["cough"],
      free_text: "",
      duration: "1_3_days",
      severity: "mild",
      age_group: "adult",
      pregnant: false,
      long_term_condition: false,
    });
  });

  it("allows submitting with only a warning sign and shows the emergency card", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/symptom-guidance");

    await user.click(await screen.findByRole("checkbox", { name: "Chest pain or pressure" }));
    await user.click(screen.getByRole("button", { name: "Get guidance" }));

    const result = await screen.findByRole("region", { name: "Your guidance" });
    expect(await within(result).findByText("Get emergency help now")).toBeInTheDocument();
    expect(within(result).queryByRole("link", { name: /request an appointment/i })).not.toBeInTheDocument();
  });

  it("clears the form with Start again", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/symptom-guidance");

    await user.click(await screen.findByRole("checkbox", { name: "Cough" }));
    await user.click(screen.getByRole("radio", { name: "1 to 3 days" }));
    await user.click(screen.getByRole("radio", { name: "Mild" }));
    await user.click(screen.getByRole("button", { name: "Get guidance" }));
    await user.click(await screen.findByRole("button", { name: "Start again" }));

    expect(screen.getByText("No guidance yet")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Cough" })).not.toBeChecked();
  });
});
