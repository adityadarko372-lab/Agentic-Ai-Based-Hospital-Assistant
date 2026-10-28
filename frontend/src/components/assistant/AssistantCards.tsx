import { Link } from "react-router-dom";

import { APPOINTMENT_STATUS } from "../../config/appointmentStatus";
import type { AppointmentRequest, AssistantCard, CareAssessment, Department } from "../../services/types";
import { formatCalendarDate } from "../../utils/dates";
import { Badge, Icon, type IconName } from "../ui";

function DepartmentRow({ department }: { department: Department }) {
  return (
    <li className="nh-chat-card__department">
      <span className="nh-service-item__icon">
        <Icon name={department.icon as IconName} size={18} />
      </span>
      <div>
        <p className="nh-chat-card__strong">{department.name}</p>
        <p className="nh-chat-card__muted">
          {department.location} · {department.opening_hours} · {department.extension}
        </p>
        {!department.accepts_appointments && <p className="nh-chat-card__muted">No appointment needed</p>}
      </div>
    </li>
  );
}

function AppointmentRow({ appointment }: { appointment: AppointmentRequest }) {
  const status = APPOINTMENT_STATUS[appointment.status];
  return (
    <li className="nh-chat-card__appointment">
      <div className="nh-request__top">
        <span className="nh-request__reference">{appointment.reference}</span>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <p className="nh-chat-card__strong">{appointment.department_name}</p>
      <p className="nh-chat-card__muted">
        Preferred {formatCalendarDate(appointment.preferred_date)} · {status.explanation}
      </p>
    </li>
  );
}

const LEVEL_TONE: Record<string, "emergency" | "pending" | "info" | "confirmed" | "neutral"> = {
  emergency: "emergency",
  urgent_same_day: "emergency",
  see_doctor_soon: "pending",
  routine: "info",
  self_care: "confirmed",
};

export function CareGuidance({ assessment }: { assessment: CareAssessment }) {
  return (
    <div className={`nh-chat-card nh-care-card nh-care-card--${assessment.level ?? "unknown"}`}>
      <div className="nh-care-card__head">
        <Badge tone={assessment.level ? LEVEL_TONE[assessment.level] : "neutral"}>{assessment.label}</Badge>
        {assessment.department_name && (
          <span className="nh-chat-card__muted">
            Suggested: <strong>{assessment.department_name}</strong>
          </span>
        )}
      </div>
      <p>{assessment.explanation}</p>
      <ul className="nh-checklist">
        {assessment.next_steps.map((step) => (
          <li key={step}>
            <Icon name="check" size={15} />
            {step}
          </li>
        ))}
      </ul>
      {assessment.can_request_appointment && assessment.department_id && (
        <Link to={`/appointments?department=${assessment.department_id}`} className="nh-button nh-button--secondary nh-button--sm">
          Request an appointment with {assessment.department_name}
        </Link>
      )}
      {assessment.reasons.length > 0 && (
        <details className="nh-care-card__why">
          <summary>Why this guidance?</summary>
          <ul>
            {assessment.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="nh-care-card__disclaimer">
        <Icon name="info" size={14} />
        {assessment.disclaimer} Rules v{assessment.rules_version}.
      </p>
    </div>
  );
}

export function EmergencyCard({ card }: { card: Extract<AssistantCard, { type: "emergency" }> }) {
  return (
    <div className="nh-chat-card nh-emergency-card" role="alert">
      <p className="nh-emergency-card__title">
        <Icon name="alert" size={20} />
        {card.self_harm ? "Please reach out for support now" : "Get emergency help now"}
      </p>
      {card.red_flags.length > 0 && <p className="nh-emergency-card__signs">Warning sign: {card.red_flags.join(", ")}</p>}
      <div className="nh-emergency-card__numbers">
        {card.numbers.map((entry) => (
          <a key={entry.number} href={`tel:${entry.number}`} className="nh-emergency-card__call">
            <span className="nh-emergency-card__number">{entry.number}</span>
            <span>{entry.label}</span>
          </a>
        ))}
      </div>
      <ul>
        {card.next_steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
    </div>
  );
}

export function HealthInfoCard({ card }: { card: Extract<AssistantCard, { type: "health_info" }> }) {
  // Only link to the https source pages that MedQuAD records.
  const safeUrl = /^https:\/\//.test(card.url) ? card.url : null;
  return (
    <div className="nh-chat-card nh-health-card">
      <div className="nh-care-card__head">
        <Badge tone="info">General information</Badge>
        <span className="nh-chat-card__muted">
          {card.source} (NIH) · match {Math.round(card.similarity * 100)}%
        </span>
      </div>
      <p className="nh-health-card__question">{card.question}</p>
      <p className="nh-health-card__answer">{card.answer}</p>
      <p className="nh-chat-card__muted nh-health-card__source">
        Source:{" "}
        {safeUrl ? (
          <a href={safeUrl} target="_blank" rel="noopener noreferrer">
            {card.source} page (opens in a new tab)
          </a>
        ) : (
          card.source
        )}{" "}
        · {card.license}
      </p>
      <p className="nh-care-card__disclaimer">
        <Icon name="info" size={14} />
        {card.disclaimer}
      </p>
    </div>
  );
}

/** Renders the structured parts of an assistant reply. */
export function AssistantCardView({ card }: { card: AssistantCard }) {
  switch (card.type) {
    case "health_info":
      return <HealthInfoCard card={card} />;
    case "emergency":
      return <EmergencyCard card={card} />;
    case "care_guidance":
      return <CareGuidance assessment={card.assessment} />;
    case "department":
      return (
        <ul className="nh-chat-card nh-chat-card--list">
          <DepartmentRow department={card.department} />
        </ul>
      );
    case "departments":
      return (
        <div className="nh-chat-card">
          <p className="nh-chat-card__title">{card.title}</p>
          <ul className="nh-chat-card--list">
            {card.items.map((department) => (
              <DepartmentRow key={department.id} department={department} />
            ))}
          </ul>
        </div>
      );
    case "checklist":
    case "steps":
      return (
        <div className="nh-chat-card">
          <p className="nh-chat-card__title">{card.title}</p>
          {card.type === "steps" ? (
            <ol className="nh-chat-card__steps">
              {card.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          ) : (
            <ul className="nh-checklist">
              {card.items.map((item) => (
                <li key={item}>
                  <Icon name="check" size={15} />
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      );
    case "appointment_draft":
      return (
        <div className="nh-chat-card nh-draft-card">
          <p className="nh-chat-card__title">{card.ready ? "Appointment request: please check" : "Appointment request so far"}</p>
          <dl className="nh-summary-list">
            <div>
              <dt>Patient</dt>
              <dd>{card.details.patient_name} (your profile)</dd>
            </div>
            <div>
              <dt>Department</dt>
              <dd>{card.details.department_name ?? "Not chosen yet"}</dd>
            </div>
            <div>
              <dt>Preferred date</dt>
              <dd>{card.details.preferred_date_label ?? "Not chosen yet"}</dd>
            </div>
            <div>
              <dt>Reason</dt>
              <dd>{card.details.reason ?? "Not given yet"}</dd>
            </div>
          </dl>
          <p className="nh-chat-card__muted">{card.note}</p>
        </div>
      );
    case "appointment_submitted":
      return (
        <div className="nh-chat-card nh-submitted-card">
          <p className="nh-success-callout__title">
            <Icon name="check" size={18} /> Request {card.appointment.reference} saved. Status: Pending
          </p>
          <ul className="nh-chat-card--list">
            <AppointmentRow appointment={card.appointment} />
          </ul>
        </div>
      );
    case "appointment_list":
      return (
        <ul className="nh-chat-card nh-chat-card--list">
          {card.items.map((appointment) => (
            <AppointmentRow key={appointment.reference} appointment={appointment} />
          ))}
        </ul>
      );
    default:
      return null;
  }
}
