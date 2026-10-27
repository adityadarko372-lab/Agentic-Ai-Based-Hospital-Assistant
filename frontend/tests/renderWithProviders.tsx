import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../src/App";
import { SESSION_STORAGE_KEY } from "../src/auth/AuthContext";
import { setAuthToken } from "../src/services/apiClient";
import type { ActivityEvent, AgentRun, AppointmentRequest, AssistantReply, Department } from "../src/services/types";
import { addDays, todayInIndia } from "../src/utils/dates";

export const HEALTHY_RESPONSE = {
  status: "ok",
  service: "Nova Health",
  version: "0.2.0-phase2",
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

export const DEMO_USER = { id: 1, email: "patient@novahealth.demo", full_name: "Asha Verma", role: "patient" };

export const DEPARTMENTS: Department[] = [
  {
    id: "general-medicine",
    name: "General Medicine",
    category: "clinical",
    summary: "Common illnesses.",
    location: "Block A, Ground Floor",
    opening_hours: "Mon–Sat, 9:00 AM – 5:00 PM",
    extension: "Ext. 2101",
    accepts_appointments: true,
    icon: "stethoscope",
  },
  {
    id: "cardiology",
    name: "Cardiology",
    category: "clinical",
    summary: "Heart care.",
    location: "Block B, First Floor",
    opening_hours: "Mon–Sat, 9:00 AM – 4:00 PM",
    extension: "Ext. 2201",
    accepts_appointments: true,
    icon: "activity",
  },
  {
    id: "emergency",
    name: "Emergency Department",
    category: "service",
    summary: "Urgent care. Call 112 / 108.",
    location: "Block D",
    opening_hours: "Open 24 hours",
    extension: "Ext. 1100",
    accepts_appointments: false,
    icon: "alert",
  },
];

export const HOSPITAL_INFO = {
  notice: "FICTIONAL demonstration content.",
  version: "test",
  hospital: {
    name: "Nova Health Multi-Speciality Hospital",
    city: "Pune (fictional)",
    is_demo: true,
    opd_hours: "Mon–Sat 9–5",
    emergency_hours: "24 hours",
    help_desk: "Main Reception",
    visiting_hours: "4–7 PM",
  },
  emergency_numbers: [
    { number: "112", label: "National emergency" },
    { number: "108", label: "Ambulance" },
  ],
  appointment_guidance: { how_to_book: [], what_to_bring: ["Photo ID"], arrival_advice: "Arrive early." },
};

export function makeAppointment(overrides: Partial<AppointmentRequest> = {}): AppointmentRequest {
  return {
    reference: "NH-APT-0001",
    patient_name: "Asha Verma",
    department_id: "cardiology",
    department_name: "Cardiology",
    preferred_date: addDays(todayInIndia(), 5),
    reason: "Follow-up for palpitations.",
    status: "pending",
    source: "form",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

interface FakeApiOptions {
  healthOnline?: boolean;
  appointments?: AppointmentRequest[];
  activity?: ActivityEvent[];
  runs?: AgentRun[];
  /** Field errors returned by POST /api/appointments (simulates server validation). */
  createFieldErrors?: Record<string, string>;
  /** Builds the assistant's reply for a message (default: a simple Patient Assistance answer). */
  assistant?: (message: string, conversationId: string | null) => AssistantReply | { status: number; detail: string };
}

export function makeRun(overrides: Partial<AgentRun> = {}): AgentRun {
  return {
    id: 1,
    conversation_id: "conv_test",
    user_message: "What should I bring to my appointment?",
    detected_intent: "hospital_info",
    confidence: 0.62,
    classifier_method: "rules",
    selected_agent: "Patient Assistance Agent",
    outcome_status: "answered",
    outcome_summary: "Listed what to bring to an appointment",
    reference: null,
    duration_ms: 12,
    created_at: new Date().toISOString(),
    steps: [
      { order: 1, agent: "Supervisory Agent", action: "receive_message", status: "ok", detail: "New message", data: {}, duration_ms: 0 },
      { order: 2, agent: "Safety Gate", action: "check_safety", status: "ok", detail: "No emergency warning signs or rule-override attempts", data: {}, duration_ms: 1 },
      {
        order: 3,
        agent: "Supervisory Agent",
        action: "classify_intent",
        status: "ok",
        detail: "Intent: hospital_info (confidence 0.62, method: rules)",
        data: { evidence: ['"what should i bring" (+3)'] },
        duration_ms: 1,
      },
      { order: 4, agent: "Supervisory Agent", action: "route_request", status: "ok", detail: "Routed to Patient Assistance Agent", data: {}, duration_ms: 0 },
      { order: 5, agent: "Patient Assistance Agent", action: "lookup_directory", status: "ok", detail: "Answered from the hospital directory", data: {}, duration_ms: 1 },
    ],
    ...overrides,
  };
}

export function makeReply(overrides: Partial<AssistantReply> = {}): AssistantReply {
  const run = overrides.run ?? makeRun();
  return {
    conversation_id: run.conversation_id,
    run_id: run.id,
    agent: run.selected_agent,
    intent: run.detected_intent,
    confidence: run.confidence,
    method: "rules",
    outcome_status: run.outcome_status,
    reply: "Here is what to bring to your appointment at Nova Health.",
    cards: [{ type: "checklist", title: "What to bring", items: ["A government photo ID"] }],
    suggestions: [{ label: "Book an appointment", message: "I want to book an appointment" }],
    sources: ["Nova Health demo directory (fictional)"],
    reference: null,
    pending_task: null,
    run,
    ...overrides,
  };
}

export interface FakeApiCall {
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/**
 * A tiny in-memory fake of the Nova Health API, installed as `fetch`.
 * It records every call so tests can assert on headers and bodies.
 */
export function mockApi(options: FakeApiOptions = {}) {
  const state = {
    appointments: [...(options.appointments ?? [])],
    activity: [...(options.activity ?? [])],
    calls: [] as FakeApiCall[],
  };

  const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = new URL(String(input), "http://localhost");
    const method = (init?.method ?? "GET").toUpperCase();
    const headers = (init?.headers ?? {}) as Record<string, string>;
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    state.calls.push({ method, path: url.pathname, headers, body });
    const signedIn = Boolean(headers.Authorization);

    if (url.pathname === "/api/health") {
      if (options.healthOnline === false) throw new TypeError("Failed to fetch");
      return json(HEALTHY_RESPONSE);
    }
    if (url.pathname === "/api/auth/login") {
      const credentials = body as { email: string; password: string };
      if (credentials.email === DEMO_USER.email && credentials.password === "NovaDemo@2026") {
        return json({ access_token: "test-token", token_type: "bearer", expires_at: "2099-01-01T00:00:00Z", user: DEMO_USER });
      }
      return json({ detail: "Incorrect email or password." }, 401);
    }
    if (url.pathname === "/api/hospital/departments") return json(DEPARTMENTS);
    if (url.pathname === "/api/hospital/info") return json(HOSPITAL_INFO);

    if (!signedIn) return json({ detail: "Please sign in to continue." }, 401);
    if (url.pathname === "/api/auth/me") return json(DEMO_USER);
    if (url.pathname === "/api/activity/mine") return json(state.activity);
    if (url.pathname === "/api/activity/runs") return json(options.runs ?? []);
    if (url.pathname === "/api/assistant/message" && method === "POST") {
      const data = body as { message: string; conversation_id: string | null };
      const result = options.assistant ? options.assistant(data.message, data.conversation_id) : makeReply();
      if ("detail" in result && "status" in result && typeof result.status === "number") {
        return json({ detail: result.detail }, result.status);
      }
      return json(result);
    }
    if (url.pathname === "/api/appointments/mine") return json(state.appointments);
    if (url.pathname === "/api/appointments" && method === "POST") {
      if (options.createFieldErrors) {
        return json({ detail: "Please correct the highlighted fields.", field_errors: options.createFieldErrors }, 422);
      }
      const data = body as { patient_name: string; department_id: string; preferred_date: string; reason: string };
      const department = DEPARTMENTS.find((d) => d.id === data.department_id)!;
      const created = makeAppointment({
        ...data,
        reference: `NH-APT-${String(state.appointments.length + 1).padStart(4, "0")}`,
        department_name: department.name,
      });
      state.appointments.unshift(created);
      return json(created, 201);
    }
    return json({ detail: "Not found" }, 404);
  });

  return { spy, state };
}

/** Simulates a stored session, as if the user had signed in earlier in this tab. */
export function signInBeforeRender() {
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, "test-token");
}

export function resetSession() {
  window.sessionStorage.clear();
  setAuthToken(null);
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
