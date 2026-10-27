/** API response shapes. These mirror backend/app/schemas.py. */

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "patient";
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: User;
}

export interface Department {
  id: string;
  name: string;
  category: "clinical" | "service";
  summary: string;
  location: string;
  opening_hours: string;
  extension: string;
  accepts_appointments: boolean;
  icon: string;
}

export interface HospitalInfo {
  notice: string;
  version: string;
  hospital: {
    name: string;
    city: string;
    is_demo: boolean;
    opd_hours: string;
    emergency_hours: string;
    help_desk: string;
    visiting_hours: string;
  };
  emergency_numbers: { number: string; label: string }[];
  appointment_guidance: {
    how_to_book: string[];
    what_to_bring: string[];
    arrival_advice: string;
  };
}

/** "pending" until the hospital reviews it; "cancelled" when the patient withdraws it. */
export type AppointmentStatus = "pending" | "cancelled" | "confirmed" | "declined";

export interface AppointmentRequest {
  reference: string;
  patient_name: string;
  department_id: string;
  department_name: string;
  preferred_date: string; // YYYY-MM-DD
  reason: string;
  status: AppointmentStatus;
  source: "form" | "assistant";
  created_at: string;
  updated_at: string;
}

export interface AppointmentCreate {
  patient_name: string;
  department_id: string;
  preferred_date: string;
  reason: string;
}

export interface ActivityEvent {
  id: number;
  event_type: string;
  actor: string;
  summary: string;
  reference: string | null;
  created_at: string;
}

// ---------- Assistant and agent trace (Phase 3) ----------

export type OutcomeStatus =
  | "answered"
  | "needs_input"
  | "action_completed"
  | "emergency_escalation"
  | "refused"
  | "clarification"
  | "information_unavailable"
  | "error";

export interface AgentStep {
  order: number;
  agent: string;
  action: string;
  status: "ok" | "warning" | "blocked" | "fallback" | "error";
  detail: string;
  data: Record<string, unknown>;
  duration_ms: number;
}

export interface AgentRun {
  id: number;
  conversation_id: string;
  user_message: string;
  detected_intent: string;
  confidence: number;
  classifier_method: string;
  selected_agent: string;
  outcome_status: OutcomeStatus;
  outcome_summary: string;
  reference: string | null;
  duration_ms: number;
  created_at: string;
  steps: AgentStep[];
}

export interface Suggestion {
  label: string;
  message?: string | null;
  href?: string | null;
}

export interface CareAssessment {
  level: "self_care" | "routine" | "see_doctor_soon" | "urgent_same_day" | "emergency" | null;
  label: string;
  explanation: string;
  next_steps: string[];
  department_id: string | null;
  department_name: string | null;
  can_request_appointment: boolean;
  matched_symptoms: { id: string; label: string; matched: string }[];
  red_flags: { id: string; label: string; matched: string }[];
  emergency_numbers: { number: string; label: string }[];
  support_numbers: { number: string; label: string }[];
  reasons: string[];
  understood: Record<string, unknown>;
  needs_more_info: string[];
  disclaimer: string;
  rules_version: string;
  clinically_reviewed: boolean;
}

export type AssistantCard =
  | { type: "department"; department: Department }
  | { type: "departments"; title: string; items: Department[] }
  | { type: "checklist"; title: string; items: string[] }
  | { type: "steps"; title: string; items: string[] }
  | {
      type: "appointment_draft";
      ready: boolean;
      note: string;
      details: {
        patient_name: string;
        department_id: string | null;
        department_name: string | null;
        preferred_date: string | null;
        preferred_date_label: string | null;
        reason: string | null;
      };
    }
  | { type: "appointment_submitted"; appointment: AppointmentRequest }
  | { type: "appointment_list"; items: AppointmentRequest[] }
  | { type: "care_guidance"; assessment: CareAssessment }
  | {
      type: "emergency";
      red_flags: string[];
      numbers: { number: string; label: string }[];
      next_steps: string[];
      self_harm: boolean;
    };

export interface AssistantReply {
  conversation_id: string;
  run_id: number;
  agent: string;
  intent: string;
  confidence: number;
  method: string;
  outcome_status: OutcomeStatus;
  reply: string;
  cards: AssistantCard[];
  suggestions: Suggestion[];
  sources: string[];
  reference: string | null;
  pending_task: string | null;
  run: AgentRun;
}
