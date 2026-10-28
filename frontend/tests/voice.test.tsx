import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { mockApi, renderApp, resetSession, signInBeforeRender } from "./renderWithProviders";

class FakeRecognition {
  static last: FakeRecognition | null = null;
  lang = "";
  interimResults = true;
  continuous = true;
  maxAlternatives = 5;
  onresult: ((event: unknown) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  started = false;
  constructor() {
    FakeRecognition.last = this;
  }
  start() {
    this.started = true;
  }
  stop() {
    this.onend?.();
  }
  abort() {
    this.onend?.();
  }
  say(text: string) {
    this.onresult?.({ resultIndex: 0, results: [{ 0: { transcript: text }, isFinal: true }] });
    this.onend?.();
  }
}

const w = window as unknown as { webkitSpeechRecognition?: unknown };

describe("Voice input (Phase 5, optional)", () => {
  beforeEach(() => resetSession());
  afterEach(() => {
    delete w.webkitSpeechRecognition;
    FakeRecognition.last = null;
  });

  it("is hidden when the browser has no speech recognition", async () => {
    mockApi();
    signInBeforeRender();
    renderApp("/assistant");
    expect(await screen.findByLabelText("Message the assistant")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Speak your message" })).not.toBeInTheDocument();
  });

  it("puts the transcript in the box (en-IN) and does not send it automatically", async () => {
    w.webkitSpeechRecognition = FakeRecognition;
    const { state } = mockApi();
    const user = userEvent.setup();
    signInBeforeRender();
    renderApp("/assistant");

    expect(await screen.findByText(/may send the audio/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Speak your message" }));
    const recognition = FakeRecognition.last!;
    expect(recognition.started).toBe(true);
    expect(recognition.lang).toBe("en-IN");
    expect(screen.getByRole("button", { name: "Stop voice input" })).toBeInTheDocument();

    act(() => recognition.say("what should I bring to my appointment"));
    expect(screen.getByLabelText("Message the assistant")).toHaveValue("what should I bring to my appointment");
    expect(state.calls.some((call) => call.path === "/api/assistant/message")).toBe(false);
  });

  it("explains a blocked microphone", async () => {
    w.webkitSpeechRecognition = FakeRecognition;
    mockApi();
    const user = userEvent.setup();
    signInBeforeRender();
    renderApp("/assistant");

    await user.click(await screen.findByRole("button", { name: "Speak your message" }));
    act(() => {
      FakeRecognition.last!.onerror?.({ error: "not-allowed" });
      FakeRecognition.last!.onend?.();
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Microphone access was blocked");
  });
});
