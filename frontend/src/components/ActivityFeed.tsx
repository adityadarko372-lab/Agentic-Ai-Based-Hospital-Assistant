import type { ActivityEvent } from "../services/types";
import { formatRelative, formatTimestamp } from "../utils/dates";
import { EmptyState, Icon, type IconName } from "./ui";

const EVENT_ICON: Record<string, IconName> = {
  "appointment.submitted": "calendar",
  "appointment.cancelled": "close",
};

interface ActivityFeedProps {
  events: ActivityEvent[];
}

/** Readable timeline of what happened and who did it. */
export function ActivityFeed({ events }: ActivityFeedProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        icon="activity"
        title="No activity yet"
        description="When you submit an appointment request (or, from Phase 3, use the assistant), each step and who handled it will appear here."
      />
    );
  }

  return (
    <ol className="nh-activity-feed">
      {events.map((event) => (
        <li key={event.id} className="nh-activity-item">
          <span className="nh-activity-item__icon">
            <Icon name={EVENT_ICON[event.event_type] ?? "activity"} size={16} />
          </span>
          <div className="nh-activity-item__body">
            <p className="nh-activity-item__summary">{event.summary}</p>
            <p className="nh-activity-item__meta">
              <span>By {event.actor}</span>
              {event.reference && <span>{event.reference}</span>}
              <time dateTime={event.created_at} title={formatTimestamp(event.created_at)}>
                {formatRelative(event.created_at)}
              </time>
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
