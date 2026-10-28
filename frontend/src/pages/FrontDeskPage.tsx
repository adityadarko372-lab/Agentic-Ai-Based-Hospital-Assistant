import { useCallback, useRef, useState } from "react";

import { PageHeader } from "../components/layout/PageHeader";
import { Badge, Button, Card, DemoDataBanner, EmptyState, Icon, Modal, Skeleton, TextArea, useToast } from "../components/ui";
import { APPOINTMENT_STATUS } from "../config/appointmentStatus";
import { useApiResource } from "../hooks/useApiResource";
import { ApiError } from "../services/apiClient";
import { frontDeskApi } from "../services/novaApi";
import type { AppointmentStatus, FrontDeskDecision, FrontDeskRequest } from "../services/types";
import { formatCalendarDate, formatTimestamp } from "../utils/dates";

type Filter = AppointmentStatus | "all";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "pending", label: "Pending" },
  { id: "confirmed", label: "Confirmed" },
  { id: "declined", label: "Declined" },
  { id: "cancelled", label: "Cancelled" },
  { id: "all", label: "All" },
];

const NOTE_LIMIT = 300;

interface PendingDecision {
  request: FrontDeskRequest;
  decision: FrontDeskDecision;
}

/**
 * Phase 5 (optional): the human-in-the-loop step. A signed-in front-desk
 * staff member confirms or declines pending requests. No agent can do this.
 */
export function FrontDeskPage() {
  const { showToast } = useToast();
  const [filter, setFilter] = useState<Filter>("pending");
  const loader = useCallback(() => frontDeskApi.list(filter), [filter]);
  const requests = useApiResource(loader);

  const [pending, setPending] = useState<PendingDecision | null>(null);
  const [note, setNote] = useState("");
  const [noteError, setNoteError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);

  // Modal re-runs its focus effect when onClose changes, so keep it stable.
  const savingRef = useRef(false);
  savingRef.current = saving;
  const closeDialog = useCallback(() => {
    if (!savingRef.current) setPending(null);
  }, []);

  function openDialog(request: FrontDeskRequest, decision: FrontDeskDecision) {
    setPending({ request, decision });
    setNote("");
    setNoteError(undefined);
  }

  async function submitDecision() {
    if (!pending) return;
    const trimmed = note.trim();
    if (pending.decision === "decline" && trimmed.length < 3) {
      setNoteError("Please add a short note for the patient explaining why.");
      return;
    }
    setSaving(true);
    try {
      const updated = await frontDeskApi.decide(pending.request.reference, pending.decision, trimmed);
      showToast({
        tone: updated.status === "confirmed" ? "success" : "info",
        title: `${updated.reference} ${updated.status}`,
        message: `The patient now sees “${APPOINTMENT_STATUS[updated.status].label}” on their Appointments page.`,
      });
      setPending(null);
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors.note) {
        setNoteError(error.fieldErrors.note);
        return;
      }
      showToast({
        tone: "error",
        title: "Decision not saved",
        message: error instanceof Error ? error.message : undefined,
      });
      setPending(null);
    } finally {
      setSaving(false);
      await requests.reload();
    }
  }

  const switchedOff = requests.errorStatus === 404;

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Front Desk Review · optional staff workflow"
        title="Front desk"
        description="Review appointment requests from patients. Only a staff member can confirm or decline a request; the AI agents never do."
      />
      <DemoDataBanner message="Demo staff view with synthetic patients. Confirming here does not book a slot in any real hospital system." />

      <Card
        as="section"
        title="Appointment requests"
        subtitle={filter === "pending" ? "Earliest preferred date first." : "Most recently updated first."}
        actions={
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<Icon name="refresh" size={14} />}
            onClick={() => void requests.reload()}
            loading={requests.loading && requests.data !== null}
            disabled={switchedOff}
          >
            Refresh
          </Button>
        }
      >
        <div className="nh-filter-bar nh-front-desk__filters" role="group" aria-label="Filter by status">
          {FILTERS.map((option) => (
            <button
              key={option.id}
              type="button"
              className={`nh-chip${filter === option.id ? " is-selected" : ""}`}
              aria-pressed={filter === option.id}
              onClick={() => setFilter(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>

        {switchedOff ? (
          <EmptyState
            icon="shield"
            title="Front-desk review is switched off"
            description="This optional feature is disabled on the server. Set FRONT_DESK_ENABLED=true in .env and restart the backend. Requests stay Pending until then."
          />
        ) : requests.loading && !requests.data ? (
          <div className="nh-stack" role="status" aria-busy="true" aria-label="Loading requests">
            <Skeleton height={110} />
            <Skeleton height={110} />
          </div>
        ) : requests.error && !requests.data ? (
          <div className="nh-status-panel">
            <p>Requests could not be loaded: {requests.error}</p>
            <Button variant="secondary" size="sm" onClick={() => void requests.reload()}>
              Try again
            </Button>
          </div>
        ) : (requests.data ?? []).length === 0 ? (
          <EmptyState
            icon="calendar"
            title={filter === "pending" ? "No requests waiting for review" : "No requests with this status"}
            description="New patient requests appear here as soon as they are submitted."
          />
        ) : (
          <ul className="nh-request-list" aria-label="Requests to review">
            {(requests.data ?? []).map((request) => (
              <FrontDeskItem key={request.reference} request={request} onDecide={openDialog} />
            ))}
          </ul>
        )}
      </Card>

      <Modal
        open={pending !== null}
        title={
          pending?.decision === "confirm"
            ? `Confirm ${pending.request.reference}?`
            : `Decline ${pending?.request.reference ?? ""}?`
        }
        onClose={closeDialog}
        actions={
          <>
            <Button variant="ghost" onClick={closeDialog} disabled={saving}>
              Back
            </Button>
            <Button
              variant={pending?.decision === "decline" ? "danger" : "primary"}
              onClick={() => void submitDecision()}
              loading={saving}
            >
              {saving ? "Saving…" : pending?.decision === "decline" ? "Decline request" : "Confirm request"}
            </Button>
          </>
        }
      >
        {pending && (
          <div className="nh-stack">
            <p>
              {pending.request.patient_name} · {pending.request.department_name} ·{" "}
              {formatCalendarDate(pending.request.preferred_date)}. A decision can be made only once and the patient
              will see it straight away.
            </p>
            <TextArea
              label={pending.decision === "decline" ? "Reason for the patient" : "Note for the patient (optional)"}
              hint={
                pending.decision === "decline"
                  ? "Required. For example: no OPD slots on that date, please pick another day."
                  : "For example: please arrive 15 minutes early with your ID."
              }
              value={note}
              maxLength={NOTE_LIMIT}
              rows={3}
              required={pending.decision === "decline"}
              error={noteError}
              onChange={(event) => {
                setNote(event.target.value);
                setNoteError(undefined);
              }}
            />
          </div>
        )}
      </Modal>
    </div>
  );
}

function FrontDeskItem({
  request,
  onDecide,
}: {
  request: FrontDeskRequest;
  onDecide: (request: FrontDeskRequest, decision: FrontDeskDecision) => void;
}) {
  const status = APPOINTMENT_STATUS[request.status];
  return (
    <li className="nh-request">
      <div className="nh-request__main">
        <div className="nh-request__top">
          <span className="nh-request__reference">{request.reference}</span>
          <Badge tone={status.tone}>{status.label}</Badge>
        </div>
        <h3 className="nh-request__department">{request.department_name}</h3>
        <p className="nh-request__meta">
          Preferred date: <strong>{formatCalendarDate(request.preferred_date)}</strong> · {request.patient_name} (
          {request.patient_email})
        </p>
        <p className="nh-request__reason">{request.reason}</p>
        <p className="nh-request__status-note">
          Submitted {formatTimestamp(request.created_at)}
          {request.source === "assistant" ? " via the AI Assistant" : " via the form"}.
          {request.reviewed_by && request.reviewed_at
            ? ` ${status.label} by ${request.reviewed_by} on ${formatTimestamp(request.reviewed_at)}.`
            : ""}
        </p>
        {request.review_note && <p className="nh-request__review-note">Note: {request.review_note}</p>}
      </div>
      {request.status === "pending" && (
        <div className="nh-request__actions">
          <Button size="sm" onClick={() => onDecide(request, "confirm")} aria-label={`Confirm request ${request.reference}`}>
            Confirm
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onDecide(request, "decline")}
            aria-label={`Decline request ${request.reference}`}
          >
            Decline
          </Button>
        </div>
      )}
    </li>
  );
}
