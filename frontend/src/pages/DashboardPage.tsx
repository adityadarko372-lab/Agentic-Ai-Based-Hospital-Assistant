import { Link } from "react-router-dom";

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
import { DEMO_DEPARTMENTS } from "../data/demoDepartments";
import { useBackendHealthContext } from "../hooks/BackendHealthContext";

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
    description: "Browse departments and what each one handles.",
    icon: "building",
  },
];

function greetingForHour(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function DashboardPage() {
  const { state, health, errorMessage, lastCheckedAt, recheck } = useBackendHealthContext();
  const greeting = greetingForHour(new Date().getHours());

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Patient dashboard"
        title={`${greeting}, welcome to Nova Health`}
        description="Your hospital assistant for finding the right department, requesting appointments and getting preliminary care guidance."
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
          title="Recent activity"
          subtitle="Requests you make and the agent that handled them."
        >
          <EmptyState
            icon="activity"
            title="No activity yet"
            description="Once you use the assistant or submit an appointment request, each step and the agent that handled it will appear here."
          />
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
            <div className="nh-stack" aria-busy="true" aria-label="Checking backend status">
              <Skeleton height={18} width="60%" />
              <Skeleton height={14} />
              <Skeleton height={14} width="80%" />
            </div>
          ) : state === "offline" ? (
            <div className="nh-status-panel nh-status-panel--offline">
              <Badge tone="emergency">Backend offline</Badge>
              <p>
                {errorMessage ?? "The server could not be reached."} Start it with{" "}
                <code>scripts\start.ps1</code> and press “Check again”.
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
                  {health &&
                  (health.features.health_info_enabled || health.features.llm_phrasing_enabled)
                    ? "Enabled"
                    : "Off (not required for the demo)"}
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

      <Card
        as="section"
        title="Hospital services"
        subtitle="Sample departments in the fictional Nova Health hospital."
        actions={
          <Link to="/services" className="nh-button nh-button--secondary nh-button--sm">
            View all
          </Link>
        }
      >
        <ul className="nh-service-grid">
          {DEMO_DEPARTMENTS.slice(0, 4).map((department) => (
            <li key={department.id} className="nh-service-item">
              <span className="nh-service-item__icon">
                <Icon name={department.icon} size={20} />
              </span>
              <div>
                <h3 className="nh-service-item__name">{department.name}</h3>
                <p className="nh-service-item__summary">{department.summary}</p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
