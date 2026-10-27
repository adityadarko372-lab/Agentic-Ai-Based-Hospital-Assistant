import type { BadgeTone } from "../components/ui";
import type { AppointmentStatus } from "../services/types";

interface StatusPresentation {
  label: string;
  tone: BadgeTone;
  explanation: string;
}

/**
 * How each status is shown. "Pending" is explicitly described as not yet
 * confirmed, because no real scheduling system is connected.
 */
export const APPOINTMENT_STATUS: Record<AppointmentStatus, StatusPresentation> = {
  pending: {
    label: "Pending",
    tone: "pending",
    explanation: "Not yet confirmed by the hospital.",
  },
  cancelled: {
    label: "Cancelled",
    tone: "neutral",
    explanation: "You withdrew this request.",
  },
  confirmed: {
    label: "Confirmed",
    tone: "confirmed",
    explanation: "Confirmed by the hospital.",
  },
  declined: {
    label: "Declined",
    tone: "emergency",
    explanation: "The hospital could not accept this request.",
  },
};
