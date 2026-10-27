import { useMemo, useRef, useState, type FormEvent } from "react";

import { ApiError } from "../../services/apiClient";
import { appointmentApi } from "../../services/novaApi";
import type { AppointmentRequest, Department } from "../../services/types";
import { addDays, formatCalendarDate, todayInIndia } from "../../utils/dates";
import { newIdempotencyKey } from "../../utils/ids";
import { Button, Icon, Modal, SelectInput, TextArea, TextInput } from "../ui";
import {
  MAX_DAYS_AHEAD,
  normaliseText,
  validateAppointmentForm,
  type AppointmentFormErrors,
  type AppointmentFormValues,
} from "./appointmentValidation";

interface AppointmentFormProps {
  departments: Department[];
  defaultPatientName: string;
  initialDepartmentId?: string;
  onSubmitted: (appointment: AppointmentRequest) => void;
}

/**
 * Module 5 form: patient name, department, preferred date and reason.
 *
 * Flow: validate → show a confirmation dialog → submit once with an
 * idempotency key → show the real reference and the Pending status.
 */
export function AppointmentForm({
  departments,
  defaultPatientName,
  initialDepartmentId = "",
  onSubmitted,
}: AppointmentFormProps) {
  const bookable = useMemo(() => departments.filter((d) => d.accepts_appointments), [departments]);
  const validInitial = bookable.some((d) => d.id === initialDepartmentId) ? initialDepartmentId : "";

  const [values, setValues] = useState<AppointmentFormValues>({
    patient_name: defaultPatientName,
    department_id: validInitial,
    preferred_date: "",
    reason: "",
  });
  const [errors, setErrors] = useState<AppointmentFormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lastSubmitted, setLastSubmitted] = useState<AppointmentRequest | null>(null);
  // One key per draft: retries of the same draft cannot create duplicates.
  const idempotencyKey = useRef(newIdempotencyKey());

  const today = todayInIndia();
  const minDate = addDays(today, 1);
  const maxDate = addDays(today, MAX_DAYS_AHEAD);
  const selectedDepartment = bookable.find((d) => d.id === values.department_id);

  function update<K extends keyof AppointmentFormValues>(field: K, value: AppointmentFormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }));
    // Clear a field's error as soon as the user edits it.
    if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function handleReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const found = validateAppointmentForm(values, departments, today);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      setConfirming(true);
    } else {
      // Move focus to the first invalid field.
      const firstField = (Object.keys(found) as (keyof AppointmentFormValues)[])[0];
      document.getElementById(`appointment-${firstField}`)?.focus();
    }
  }

  async function handleConfirm() {
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await appointmentApi.create(
        {
          patient_name: normaliseText(values.patient_name),
          department_id: values.department_id,
          preferred_date: values.preferred_date,
          reason: normaliseText(values.reason),
        },
        idempotencyKey.current,
      );
      setConfirming(false);
      setLastSubmitted(created);
      setValues((current) => ({ ...current, department_id: "", preferred_date: "", reason: "" }));
      idempotencyKey.current = newIdempotencyKey();
      onSubmitted(created);
    } catch (error) {
      setConfirming(false);
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(error.fieldErrors as AppointmentFormErrors);
        setFormError(error.message);
      } else {
        // Same key is kept, so pressing Submit again is a safe retry.
        setFormError(
          `${error instanceof Error ? error.message : "The request could not be submitted."} Nothing was saved twice; you can safely try again.`,
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {lastSubmitted && (
        <div className="nh-success-callout" role="status">
          <Icon name="check" size={20} />
          <div>
            <p className="nh-success-callout__title">
              Request {lastSubmitted.reference} submitted. Status: Pending
            </p>
            <p>
              Saved for {lastSubmitted.department_name} on {formatCalendarDate(lastSubmitted.preferred_date)}. This is
              a request, not a confirmed appointment; the hospital still needs to review it.
            </p>
          </div>
        </div>
      )}

      {formError && (
        <p className="nh-inline-alert nh-inline-alert--error" role="alert">
          <Icon name="alert" size={16} />
          {formError}
        </p>
      )}

      <form className="nh-stack nh-appointment-form" onSubmit={handleReview} noValidate aria-label="Appointment request">
        <TextInput
          id="appointment-patient_name"
          label="Patient name"
          autoComplete="name"
          value={values.patient_name}
          onChange={(event) => update("patient_name", event.target.value)}
          error={errors.patient_name}
          hint="Prefilled from your profile. Change it if you are booking for a family member."
          required
        />
        <SelectInput
          id="appointment-department_id"
          label="Department"
          value={values.department_id}
          onChange={(event) => update("department_id", event.target.value)}
          error={errors.department_id}
          hint={selectedDepartment ? `${selectedDepartment.location} · ${selectedDepartment.opening_hours}` : undefined}
          required
        >
          <option value="" disabled>
            Select a department
          </option>
          {bookable.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </SelectInput>
        <TextInput
          id="appointment-preferred_date"
          label="Preferred date"
          type="date"
          min={minDate}
          max={maxDate}
          value={values.preferred_date}
          onChange={(event) => update("preferred_date", event.target.value)}
          error={errors.preferred_date}
          hint={`Choose a date between ${formatCalendarDate(minDate)} and ${formatCalendarDate(maxDate)}.`}
          required
        />
        <TextArea
          id="appointment-reason"
          label="Reason for appointment"
          value={values.reason}
          maxLength={500}
          onChange={(event) => update("reason", event.target.value)}
          error={errors.reason}
          hint={`Briefly describe why you would like to be seen (${normaliseText(values.reason).length}/500). For an emergency, call 112 or 108 instead.`}
          required
        />
        <div className="nh-form-actions">
          <Button type="submit">Review request</Button>
        </div>
      </form>

      <Modal
        open={confirming}
        title="Submit this appointment request?"
        onClose={() => !submitting && setConfirming(false)}
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirming(false)} disabled={submitting}>
              Edit details
            </Button>
            <Button onClick={handleConfirm} loading={submitting}>
              {submitting ? "Submitting…" : "Submit request"}
            </Button>
          </>
        }
      >
        <dl className="nh-summary-list">
          <div>
            <dt>Patient</dt>
            <dd>{normaliseText(values.patient_name)}</dd>
          </div>
          <div>
            <dt>Department</dt>
            <dd>{selectedDepartment?.name}</dd>
          </div>
          <div>
            <dt>Preferred date</dt>
            <dd>{values.preferred_date && formatCalendarDate(values.preferred_date)}</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>{normaliseText(values.reason)}</dd>
          </div>
        </dl>
        <p className="nh-modal__note">
          It will be saved with the status <strong>Pending</strong>. It is not a confirmed appointment until the
          hospital reviews it.
        </p>
      </Modal>
    </>
  );
}
