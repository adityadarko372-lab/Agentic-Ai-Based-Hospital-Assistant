import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { CHAT_STORAGE_PREFIX } from "../src/hooks/useAssistantChat";
import { makeAppointment, makeReply, makeRun, mockApi, renderApp, resetSession, signInBeforeRender } from "./renderWithProviders";

const emergencyReply = makeReply({
  agent: "Care Navigation Agent",
  intent: "emergency",
  outcome_status: "emergency_escalation",
  reply: "This could be an emergency (chest pain or pressure). Please call 112 or 108 now.",
  cards: [
    {
      type: "emergency",
      red_flags: ["Chest pain or pressure"],
      numbers: [
        { number: "112", label: "National emergency number (India)" },
        { number: "108", label: "Emergency ambulance service" },
      ],
      next_steps: ["Call 112 or 108 now."],
      self_harm: false,
    },
  ],
  run: makeRun({
    id: 2,
    detected_intent: "emergency",
    confidence: 1,
    classifier_method: "safety_rules",
    selected_agent: "Care Navigation Agent",
    outcome_status: "emergency_escalation",
    steps: [
      { order: 1, agent: "Supervisory Agent", action: "receive_message", status: "ok", detail: "New message", data: {}, duration_ms: 0 },
      { order: 2, agent: "Safety Gate", action: "check_safety", status: "warning", detail: "Emergency warning sign(s): Chest pain or pressure", data: {}, duration_ms: 1 },
    ],
  }),
});

describe("AI Assistant (Modules 2 and 3)", () => {
  beforeEach(() => {
    resetSession();
    signInBeforeRender();
  });

  it("offers the specification's example questions as starters", async () => {
    mockApi();
    renderApp("/assistant");

    const chips = await screen.findByRole("group", { name: /suggested replies/i });
    for (const label of [/which department/i, /what should i bring/i, /how do i book/i, /hospital services/i]) {
      expect(within(chips).getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText("No activity yet")).toBeInTheDocument();
  });

  it("sends a message, shows the agent's answer and the activity trace", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/assistant");

    await user.type(await screen.findByLabelText(/message the assistant/i), "What should I bring to my appointment?");
    await user.click(screen.getByRole("button", { name: "Send message" }));

    const log = screen.getByRole("log", { name: "Messages" });
    expect(await within(log).findByText(/here is what to bring/i)).toBeInTheDocument();
    expect(within(log).getByText("Patient Assistance Agent")).toBeInTheDocument();
    expect(within(log).getByText("A government photo ID")).toBeInTheDocument();
    expect(within(log).getByText(/source: nova health demo directory/i)).toBeInTheDocument();

    // Activity panel shows the routing decision with confidence and evidence.
    const steps = screen.getByRole("list", { name: "Agent steps" });
    expect(within(steps).getByText("Safety check")).toBeInTheDocument();
    expect(within(steps).getByText("Intent detection")).toBeInTheDocument();
    expect(within(steps).getByText('"what should i bring" (+3)')).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: /routing confidence/i })).toHaveAttribute("aria-valuenow", "62");

    const post = state.calls.find((call) => call.path === "/api/assistant/message")!;
    expect(post.body).toEqual({ message: "What should I bring to my appointment?", conversation_id: null });
  });

  it("sends with Enter, keeps the conversation id and uses suggestion chips", async () => {
    const { state } = mockApi();
    const user = userEvent.setup();
    renderApp("/assistant");

    await user.type(await screen.findByLabelText(/message the assistant/i), "hello{Enter}");
    await screen.findByText(/here is what to bring/i);
    await user.click(screen.getByRole("button", { name: "Book an appointment" }));

    const posts = state.calls.filter((call) => call.path === "/api/assistant/message");
    expect(posts).toHaveLength(2);
    expect(posts[1].body).toEqual({ message: "I want to book an appointment", conversation_id: "conv_test" });
  });

  it("shows emergency guidance with tappable 112 and 108", async () => {
    mockApi({ assistant: () => emergencyReply });
    const user = userEvent.setup();
    renderApp("/assistant");

    await user.type(await screen.findByLabelText(/message the assistant/i), "I have chest pain{Enter}");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Get emergency help now");
    expect(within(alert).getByRole("link", { name: /112/ })).toHaveAttribute("href", "tel:112");
    expect(within(alert).getByRole("link", { name: /108/ })).toHaveAttribute("href", "tel:108");
    expect(screen.getAllByText("Emergency guidance").length).toBeGreaterThan(0);
  });

  it("shows a submitted request as Pending, never as confirmed", async () => {
    mockApi({
      assistant: () =>
        makeReply({
          agent: "Appointment Agent",
          outcome_status: "action_completed",
          reply: "Done. Your request NH-APT-0004 has been saved with the status Pending.",
          reference: "NH-APT-0004",
          cards: [{ type: "appointment_submitted", appointment: makeAppointment({ reference: "NH-APT-0004", source: "assistant" }) }],
          run: makeRun({ selected_agent: "Appointment Agent", outcome_status: "action_completed", reference: "NH-APT-0004" }),
        }),
    });
    const user = userEvent.setup();
    renderApp("/assistant");

    await user.type(await screen.findByLabelText(/message the assistant/i), "yes{Enter}");

    expect(await screen.findByText(/Request NH-APT-0004 saved\. Status: Pending/)).toBeInTheDocument();
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Confirmed$/)).not.toBeInTheDocument();
  });

  it("reports a failed request honestly and keeps the page usable", async () => {
    mockApi({ assistant: () => ({ status: 500, detail: "Internal error." }) });
    const user = userEvent.setup();
    renderApp("/assistant");

    await user.type(await screen.findByLabelText(/message the assistant/i), "hello{Enter}");

    expect(await screen.findByText(/your message was not processed/i)).toBeInTheDocument();
    expect(screen.getByText("Not delivered")).toBeInTheDocument();
    expect(screen.getByLabelText(/message the assistant/i)).toBeEnabled();
  });

  it("clears stored chat history on sign-out", async () => {
    mockApi();
    const user = userEvent.setup();
    renderApp("/assistant");

    await user.type(await screen.findByLabelText(/message the assistant/i), "hello{Enter}");
    await screen.findByText(/here is what to bring/i);
    expect(window.sessionStorage.getItem(`${CHAT_STORAGE_PREFIX}1`)).not.toBeNull();

    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(window.sessionStorage.getItem(`${CHAT_STORAGE_PREFIX}1`)).toBeNull();
  });
});

describe("Agent Activity page", () => {
  beforeEach(() => {
    resetSession();
    signInBeforeRender();
  });

  it("lists runs, filters by agent and expands the steps", async () => {
    mockApi({
      runs: [
        makeRun({ id: 3, selected_agent: "Appointment Agent", user_message: "I want to book an appointment", detected_intent: "appointment_book" }),
        makeRun({ id: 2 }),
      ],
    });
    const user = userEvent.setup();
    renderApp("/activity");

    const list = await screen.findByRole("list", { name: "Agent runs" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: /^appointment \(1\)/i }));
    expect(within(screen.getByRole("list", { name: "Agent runs" })).getAllByRole("listitem")).toHaveLength(1);

    const summary = screen.getByRole("button", { name: /i want to book an appointment/i });
    expect(summary).toHaveAttribute("aria-expanded", "false");
    await user.click(summary);
    expect(summary).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("list", { name: "Agent steps" })).toBeInTheDocument();
  });

  it("shows an empty state with a link to the assistant", async () => {
    mockApi();
    renderApp("/activity");

    expect(await screen.findByText("No agent activity yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open the assistant" })).toHaveAttribute("href", "/assistant");
  });
});
