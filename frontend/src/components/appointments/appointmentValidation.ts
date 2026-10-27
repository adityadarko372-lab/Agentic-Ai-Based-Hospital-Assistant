/**
 * Client-side checks for the appointment form. They mirror the backend rules
 * (backend/app/schemas.py and services/appointment_service.py) so patients get
 * instant feedback. The backend still re-validates everything.
 */
import type { Department } from "../../services/types";
import { addDays } from "../../utils/dates";

export const MAX_DAYS_AHEAD = 90;

export interface AppointmentFormValues {
  patient_name: string;
  department_id: string;
  preferred_date: string;
  reason: string;
}

export type AppointmentFormErrors = Partial<Record<keyof AppointmentFormValues, string>>;

// Letters plus combining marks (\p{M}) so Indian scripts such as Devanagari,
// whose vowel signs are marks, are accepted. Separators: space . ' -
// Same shape as the backend rule: word, then (". " | "." | " " | "'" | "-") + word, optional final ".".
const NAME_PATTERN = /^\p{L}[\p{L}\p{M}]*(?:(?:\. ?|[ '-])\p{L}[\p{L}\p{M}]*)*\.?$/u;

export function normaliseText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function validateAppointmentForm(
  values: AppointmentFormValues,
  departments: Department[],
  today: string,
): AppointmentFormErrors {
  const errors: AppointmentFormErrors = {};
  const name = normaliseText(values.patient_name);
  const reason = normaliseText(values.reason);

  if (name.length < 2) errors.patient_name = "Please enter the patient's full name.";
  else if (name.length > 80) errors.patient_name = "Please keep the name under 80 characters.";
  else if (!NAME_PATTERN.test(name))
    errors.patient_name = "Names can contain letters, spaces, dots, apostrophes and hyphens only.";

  const department = departments.find((item) => item.id === values.department_id);
  if (!values.department_id) errors.department_id = "Please choose a department.";
  else if (!department) errors.department_id = "Please choose a department from the list.";
  else if (!department.accepts_appointments)
    errors.department_id = `${department.name} does not take appointment requests.`;

  if (!values.preferred_date) errors.preferred_date = "Please choose a preferred date.";
  else if (values.preferred_date <= today) errors.preferred_date = "Please choose a date from tomorrow onwards.";
  else if (values.preferred_date > addDays(today, MAX_DAYS_AHEAD))
    errors.preferred_date = `Please choose a date within the next ${MAX_DAYS_AHEAD} days.`;

  if (reason.length < 10) errors.reason = "Please describe the reason in at least 10 characters.";
  else if (reason.length > 500) errors.reason = "Please keep the reason under 500 characters.";

  return errors;
}
