import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../src/App";

export const HEALTHY_RESPONSE = {
  status: "ok",
  service: "Nova Health",
  version: "0.1.0-phase1",
  environment: "test",
  demo_data: true,
  server_time: "2026-10-26T10:00:00Z",
  features: {
    intent_classifier: "rules",
    health_info_enabled: false,
    llm_phrasing_enabled: false,
    front_desk_enabled: false,
  },
};

/** Mocks fetch so /api/health succeeds (or fails when `online` is false). */
export function mockHealthFetch(online = true) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
    if (!online) throw new TypeError("Failed to fetch");
    return new Response(JSON.stringify(HEALTHY_RESPONSE), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

export function renderApp(initialPath = "/"): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <App />
    </MemoryRouter>,
  );
}

export function renderUi(ui: ReactElement) {
  return render(ui);
}
