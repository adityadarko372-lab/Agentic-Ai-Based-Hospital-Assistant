import type { IconName } from "../components/ui";
import type { OutcomeStatus } from "../services/types";

export interface AgentPresentation {
  short: string;
  icon: IconName;
  tone: "supervisor" | "safety" | "assistance" | "appointment" | "care";
  role: string;
}

/** How each agent is labelled in the chat and the Agent Activity panel. */
export const AGENTS: Record<string, AgentPresentation> = {
  "Supervisory Agent": { short: "Supervisor", icon: "sparkle", tone: "supervisor", role: "Understands the request and routes it" },
  "Safety Gate": { short: "Safety Gate", icon: "shield", tone: "safety", role: "Checks for warning signs and rule-override attempts" },
  "Patient Assistance Agent": { short: "Patient Assistance", icon: "building", tone: "assistance", role: "Hospital services and departments" },
  "Appointment Agent": { short: "Appointment", icon: "calendar", tone: "appointment", role: "Appointment requests" },
  "Care Navigation Agent": { short: "Care Navigation", icon: "stethoscope", tone: "care", role: "Preliminary care guidance" },
};

export function agentPresentation(agent: string): AgentPresentation {
  return AGENTS[agent] ?? { short: agent, icon: "activity", tone: "supervisor", role: "" };
}

export const ACTION_LABELS: Record<string, string> = {
  receive_message: "Received the message",
  check_safety: "Safety check",
  select_classifier: "Classifier selection",
  classify_intent: "Intent detection",
  route_request: "Routing decision",
  update_context: "Conversation context",
  identify_topic: "Identified the topic",
  lookup_directory: "Looked up the hospital directory",
  start_booking: "Started a request",
  continue_booking: "Continued the request",
  extract_details: "Read booking details",
  ask_for_detail: "Asked for a detail",
  await_confirmation: "Waiting for confirmation",
  save_request: "Saved to the database",
  abandon_draft: "Stopped without saving",
  lookup_requests: "Read your requests",
  lookup_request: "Looked up a request",
  cancel_request: "Cancellation",
  apply_care_rules: "Applied care-navigation rules",
  ask_followup: "Asked a follow-up question",
  combine_answers: "Combined answers",
  compose_reply: "Composed the reply",
  record_outcome: "Recorded the outcome",
};

export const OUTCOME_LABELS: Record<OutcomeStatus, { label: string; tone: "pending" | "confirmed" | "emergency" | "info" | "neutral" }> = {
  answered: { label: "Answered", tone: "confirmed" },
  needs_input: { label: "Needs your input", tone: "pending" },
  action_completed: { label: "Action completed", tone: "confirmed" },
  emergency_escalation: { label: "Emergency guidance", tone: "emergency" },
  refused: { label: "Declined", tone: "neutral" },
  clarification: { label: "Asked to clarify", tone: "info" },
  information_unavailable: { label: "Information unavailable", tone: "neutral" },
  error: { label: "Error", tone: "emergency" },
};

export function intentLabel(intent: string): string {
  return intent.replace(/_/g, " ");
}
