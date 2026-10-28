import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ActivityFeed } from "../components/ActivityFeed";
import { EmergencyNotice } from "../components/EmergencyNotice";
import { PageHeader } from "../components/layout/PageHeader";
import {
  Badge,
  Button,
  Card,
  DemoDataBanner,
  EmptyState,
  Icon,
  Skeleton,
  type IconName,
} from "../components/ui";
import { APPOINTMENT_STATUS } from "../config/appointmentStatus";
import { useBackendHealthContext } from "../hooks/BackendHealthContext";
import { useApiResource } from "../hooks/useApiResource";
import { activityApi, appointmentApi, hospitalApi } from "../services/novaApi";
import { formatCalendarDate, todayInIndia } from "../utils/dates";

interface QuickAction {
  to: string;
  title: string;
  description: string;
  icon: IconName;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    to: "/assistant",
    title: "AI Assistant",
    description: "Ask about departments, appointments or hospital services.",
    icon: "chat",
  },
  {
    to: "/symptom-guidance",
    title: "Symptom Guidance",
    description: "Get cautious, preliminary guidance on where to seek care.",
    icon: "stethoscope",
  },
  {
    to: "/appointments",
    title: "Book Appointment",
    description: "Submit an appointment request and track its status.",
    icon: "calendar",
  },
  {
    to: "/services",
    title: "Hospital Services",
    description: "Browse departments, locations and timings.",
    icon: "building",
  },
];

// Stable loaders (useApiResource re-runs when the loader changes).
const loadRecentActivity = () => activityApi.mine(6);

function greetingForHour(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function LoadingRows({ label, rows = 3 }: { label: string; rows?: number }) {
  return (
    <div className="nh-stack" role="status" aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} height={52} />
      ))}
    </div>
  );
}

function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="nh-status-panel">
      <p>{message}</p>
      <Button variant="secondary" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

/** Module 1: Patient Dashboard. */
export function DashboardPage() {
  const { user } = useAuth();
  const { state, health, errorMessage, lastCheckedAt, recheck } = useBackendHealthContext();
  const activity = useApiResource(loadRecentActivity);
  const requests = useApiResource(appointmentApi.mine);
  const departments = useApiResource(hospitalApi.departments);

  const firstName = user?.full_name.split(" ")[0] ?? "there";
  const greeting = greetingForHour(new Date().getHours());
  const today = todayInIndia();
  const upcoming = (requests.data ?? [])
    .filter((request) => request.status === "pending" && request.preferred_date > today)
    .sort((a, b) => a.preferred_date.localeCompare(b.preferred_date))
    .slice(0, 3);
  const featuredDepartments = (departments.data ?? []).filter((d) => d.category === "clinical").slice(0, 4);

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Patient dashboard"
        title={`${greeting}, ${firstName}`}
        description="Welcome to Nova Health. Find the right department, request appointments and get preliminary care guidance."
        actions={
          <Link to="/assistant" className="nh-button nh-button--primary">
            <Icon name="sparkle" size={18} />
            Ask the assistant
          </Link>
        }
      />

      <DemoDataBanner />
      <EmergencyNotice />

      <section aria-labelledby="quick-actions-heading">
        <h2 id="quick-actions-heading" className="nh-section-title">
          Quick access
        </h2>
        <ul className="nh-quick-grid">
          {QUICK_ACTIONS.map((action) => (
            <li key={action.to}>
              <Link to={action.to} className="nh-quick-card">
                <span className="nh-quick-card__icon">
                  <Icon name={action.icon} size={24} />
                </span>
                <span className="nh-quick-card__title">{action.title}</span>
                <span className="nh-quick-card__description">{action.description}</span>
                <span className="nh-quick-card__cta">
                  Open <Icon name="chevronRight" size={16} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <div className="nh-dashboard-columns">
        <Card
          as="section"
          title="Upcoming requests"
          subtitle="Pending requests for future dates. Not yet confirmed by the hospital."
          actions={
            <Link to="/appointments" className="nh-button nh-button--secondary nh-button--sm">
              Manage
            </Link>
          }
        >
          {requests.loading && !requests.data ? (
            <LoadingRows label="Loading your requests" rows={2} />
          ) : requests.error && !requests.data ? (
            <LoadError message={`Requests could not be loaded: ${requests.error}`} onRetry={() => void requests.reload()} />
          ) : upcoming.length === 0 ? (
            <EmptyState
              icon="calendar"
              title="No upcoming requests"
              description="Submit an appointment request and it will appear here with its status."
              action={
                <Link to="/appointments" className="nh-button nh-button--primary nh-button--sm">
                  Request an appointment
                </Link>
              }
            />
          ) : (
            <ul className="nh-upcoming-list">
              {upcoming.map((request) => (
                <li key={request.reference} className="nh-upcoming">
                  <div className="nh-upcoming__date" aria-hidden="true">
                    <span>{formatCalendarDate(request.preferred_date).split(" ")[0]}</span>
                    <span>{formatCalendarDate(request.preferred_date).split(" ")[1]}</span>
                  </div>
                  <div className="nh-upcoming__body">
                    <p className="nh-upcoming__title">{request.department_name}</p>
                    <p className="nh-upcoming__meta">
                      {request.reference} · preferred {formatCalendarDate(request.preferred_date)}
                    </p>
                  </div>
                  <Badge tone={APPOINTMENT_STATUS[request.status].tone}>{APPOINTMENT_STATUS[request.status].label}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card as="section" title="Recent activity" subtitle="What happened and who handled it.">
          {activity.loading && !activity.data ? (
            <LoadingRows label="Loading recent activity" />
          ) : activity.error && !activity.data ? (
            <LoadError message={`Activity could not be loaded: ${activity.error}`} onRetry={() => void activity.reload()} />
          ) : (
            <ActivityFeed events={activity.data ?? []} />
          )}
        </Card>
      </div>

      <div className="nh-dashboard-columns">
        <Card
          as="section"
          title="Hospital services"
          subtitle="Departments in the fictional Nova Health hospital."
          actions={
            <Link to="/services" className="nh-button nh-button--secondary nh-button--sm">
              View all
            </Link>
          }
        >
          {departments.loading && !departments.data ? (
            <LoadingRows label="Loading departments" rows={2} />
          ) : departments.error && !departments.data ? (
            <LoadError
              message={`Departments could not be loaded: ${departments.error}`}
              onRetry={() => void departments.reload()}
            />
          ) : (
            <ul className="nh-service-grid nh-service-grid--compact">
              {featuredDepartments.map((department) => (
                <li key={department.id} className="nh-service-item">
                  <span className="nh-service-item__icon">
                    <Icon name={department.icon as IconName} size={20} />
                  </span>
                  <div>
                    <h3 className="nh-service-item__name">{department.name}</h3>
                    <p className="nh-service-item__summary">{department.location}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          as="section"
          title="System status"
          subtitle="What is running in this prototype right now."
          actions={
            <Button
              variant="secondary"
              size="sm"
              leadingIcon={<Icon name="refresh" size={14} />}
              onClick={recheck}
              loading={state === "checking"}
            >
              Check again
            </Button>
          }
        >
          {state === "checking" && !health ? (
            <LoadingRows label="Checking backend status" rows={2} />
          ) : state === "offline" ? (
            <div className="nh-status-panel nh-status-panel--offline">
              <Badge tone="emergency">Backend offline</Badge>
              <p>
                {errorMessage ?? "The server could not be reached."} Start it with <code>scripts\start.ps1</code> and
                press “Check again”.
              </p>
            </div>
          ) : (
            <dl className="nh-status-list">
              <div>
                <dt>API</dt>
                <dd>
                  <Badge tone="confirmed">Backend connected</Badge>
                </dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{health?.version}</dd>
              </div>
              <div>
                <dt>Request routing</dt>
                <dd>
                  {health?.features.intent_classifier === "rules"
                    ? "Transparent rules (default)"
                    : "Trained classifier (optional)"}
                </dd>
              </div>
              <div>
                <dt>Optional AI add-ons</dt>
                <dd>
                  {health && (health.features.health_info_enabled || health.features.llm_phrasing_enabled)
                    ? "Enabled"
                    : "Off (not required)"}
                </dd>
              </div>
              <div>
                <dt>Data</dt>
                <dd>{health?.demo_data ? "Synthetic demo data" : "Unknown"}</dd>
              </div>
              {lastCheckedAt && (
                <div>
                  <dt>Last checked</dt>
                  <dd>{lastCheckedAt.toLocaleTimeString("en-IN")}</dd>
                </div>
              )}
            </dl>
          )}
        </Card>
      </div>
    </div>
  );
}
