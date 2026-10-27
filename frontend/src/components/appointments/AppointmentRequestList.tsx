import { useState } from "react";

import { APPOINTMENT_STATUS } from "../../config/appointmentStatus";
import type { AppointmentRequest } from "../../services/types";
import { formatCalendarDate, formatTimestamp } from "../../utils/dates";
import { Badge, Button, EmptyState, Modal } from "../ui";

interface AppointmentRequestListProps {
  requests: AppointmentRequest[];
  onCancel: (reference: string) => Promise<void>;
}

/** "My requests": every request with its real, stored status. */
export function AppointmentRequestList({ requests, onCancel }: AppointmentRequestListProps) {
  const [toCancel, setToCancel] = useState<AppointmentRequest | null>(null);
  const [cancelling, setCancelling] = useState(false);

  if (requests.length === 0) {
    return (
      <EmptyState
        icon="calendar"
        title="No requests yet"
        description="Requests you submit are saved here with their current status."
      />
    );
  }

  async function confirmCancel() {
    if (!toCancel) return;
    setCancelling(true);
    try {
      await onCancel(toCancel.reference);
      setToCancel(null);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <>
      <ul className="nh-request-list" aria-label="Your appointment requests">
        {requests.map((request) => {
          const status = APPOINTMENT_STATUS[request.status];
          return (
            <li key={request.reference} className="nh-request">
              <div className="nh-request__main">
                <div className="nh-request__top">
                  <span className="nh-request__reference">{request.reference}</span>
                  <Badge tone={status.tone}>{status.label}</Badge>
                </div>
                <h3 className="nh-request__department">{request.department_name}</h3>
                <p className="nh-request__meta">
                  Preferred date: <strong>{formatCalendarDate(request.preferred_date)}</strong> · for{" "}
                  {request.patient_name}
                </p>
                <p className="nh-request__reason">{request.reason}</p>
                <p className="nh-request__status-note">
                  {status.explanation} Submitted {formatTimestamp(request.created_at)}
                  {request.source === "assistant" ? " via the AI Assistant" : ""}.
                </p>
              </div>
              {request.status === "pending" && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setToCancel(request)}
                  aria-label={`Cancel request ${request.reference}`}
                >
                  Cancel request
                </Button>
              )}
            </li>
          );
        })}
      </ul>

      <Modal
        open={toCancel !== null}
        title="Cancel this request?"
        onClose={() => !cancelling && setToCancel(null)}
        actions={
          <>
            <Button variant="ghost" onClick={() => setToCancel(null)} disabled={cancelling}>
              Keep request
            </Button>
            <Button variant="danger" onClick={confirmCancel} loading={cancelling}>
              {cancelling ? "Cancelling…" : "Cancel request"}
            </Button>
          </>
        }
      >
        <p>
          Request {toCancel?.reference} to {toCancel?.department_name} will be withdrawn. This cannot be undone; you can
          submit a new request at any time.
        </p>
      </Modal>
    </>
  );
}
