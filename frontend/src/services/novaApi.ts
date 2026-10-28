/** One function per backend endpoint, so pages never build URLs themselves. */
import { apiGet, apiPost } from "./apiClient";
import type {
  ActivityEvent,
  AgentRun,
  AssistantReply,
  AppointmentCreate,
  CareAssessRequest,
  CareAssessResponse,
  CareFormOptions,
  AppointmentRequest,
  Department,
  HospitalInfo,
  LoginResponse,
  User,
} from "./types";

export const authApi = {
  login: (email: string, password: string) =>
    apiPost<LoginResponse>("/api/auth/login", { email, password }, { notifyOnUnauthorized: false }),
  me: () => apiGet<User>("/api/auth/me"),
};

export const hospitalApi = {
  departments: () => apiGet<Department[]>("/api/hospital/departments"),
  info: () => apiGet<HospitalInfo>("/api/hospital/info"),
};

export const appointmentApi = {
  /**
   * The idempotency key makes a repeated submission (double click, retry)
   * return the original request instead of creating a duplicate.
   */
  create: (data: AppointmentCreate, idempotencyKey: string) =>
    apiPost<AppointmentRequest>("/api/appointments", data, { headers: { "Idempotency-Key": idempotencyKey } }),
  mine: () => apiGet<AppointmentRequest[]>("/api/appointments/mine"),
  cancel: (reference: string) =>
    apiPost<AppointmentRequest>(`/api/appointments/${encodeURIComponent(reference)}/cancel`),
};

export const activityApi = {
  mine: (limit = 20) => apiGet<ActivityEvent[]>(`/api/activity/mine?limit=${limit}`),
  runs: (limit = 30) => apiGet<AgentRun[]>(`/api/activity/runs?limit=${limit}`),
  run: (runId: number) => apiGet<AgentRun>(`/api/activity/runs/${runId}`),
};

export const careApi = {
  options: () => apiGet<CareFormOptions>("/api/care-navigation/options"),
  assess: (data: CareAssessRequest) => apiPost<CareAssessResponse>("/api/care-navigation/assess", data),
};

export const assistantApi = {
  /** The Supervisory Agent can take a moment on the first call, so allow 15 s. */
  send: (message: string, conversationId: string | null) =>
    apiPost<AssistantReply>(
      "/api/assistant/message",
      { message, conversation_id: conversationId },
      { timeoutMs: 15000 },
    ),
};
