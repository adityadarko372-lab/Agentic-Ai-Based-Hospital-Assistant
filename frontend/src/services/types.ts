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
