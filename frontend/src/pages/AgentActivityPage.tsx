import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { AgentTimeline } from "../components/assistant/AgentTimeline";
import { PageHeader } from "../components/layout/PageHeader";
import { Badge, Button, Card, DemoDataBanner, EmptyState, Icon, Skeleton } from "../components/ui";
import { AGENTS, agentPresentation, intentLabel, OUTCOME_LABELS } from "../config/agents";
import { useApiResource } from "../hooks/useApiResource";
import { activityApi } from "../services/novaApi";
import { formatRelative, formatTimestamp } from "../utils/dates";

const loadRuns = () => activityApi.runs(50);
const SPECIALISTS = Object.keys(AGENTS).filter((name) => name !== "Safety Gate");

/** Module 3: history of which agent handled each request and what happened. */
export function AgentActivityPage() {
  const runs = useApiResource(loadRuns);
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [openRunId, setOpenRunId] = useState<number | null>(null);

  const visible = useMemo(
    () => (runs.data ?? []).filter((run) => agentFilter === "all" || run.selected_agent === agentFilter),
    [runs.data, agentFilter],
  );
  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const run of runs.data ?? []) result[run.selected_agent] = (result[run.selected_agent] ?? 0) + 1;
    return result;
  }, [runs.data]);

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Module 3 · Multi-Agent System"
        title="Agent Activity"
        description="Every assistant request, which agent handled it, why, and the real outcome. Saved in the database, newest first."
        actions={
          <Button variant="secondary" size="sm" leadingIcon={<Icon name="refresh" size={14} />} onClick={() => void runs.reload()} loading={runs.loading && runs.data !== null}>
            Refresh
          </Button>
        }
      />
      <DemoDataBanner message="Only your own requests are shown. Routing uses transparent rules; the optional trained classifier is off." />

      <div className="nh-filter-bar" role="group" aria-label="Filter by agent">
        <button type="button" className={`nh-chip${agentFilter === "all" ? " is-selected" : ""}`} aria-pressed={agentFilter === "all"} onClick={() => setAgentFilter("all")}>
          All agents ({runs.data?.length ?? 0})
        </button>
        {SPECIALISTS.map((agent) => (
          <button
            key={agent}
            type="button"
            className={`nh-chip${agentFilter === agent ? " is-selected" : ""}`}
            aria-pressed={agentFilter === agent}
            onClick={() => setAgentFilter(agent)}
          >
            {agentPresentation(agent).short} ({counts[agent] ?? 0})
          </button>
        ))}
      </div>

      <Card as="section" title="Requests" subtitle="Select a request to see every step.">
        {runs.loading && !runs.data ? (
          <div className="nh-stack" role="status" aria-busy="true" aria-label="Loading agent activity">
            <Skeleton height={64} />
            <Skeleton height={64} />
            <Skeleton height={64} />
          </div>
        ) : runs.error && !runs.data ? (
          <div className="nh-status-panel">
            <p>Agent activity could not be loaded: {runs.error}</p>
            <Button variant="secondary" size="sm" onClick={() => void runs.reload()}>
              Try again
            </Button>
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            icon="activity"
            title="No agent activity yet"
            description="Ask the assistant something and the request will appear here with every step."
            action={
              <Link to="/assistant" className="nh-button nh-button--primary nh-button--sm">
                Open the assistant
              </Link>
            }
          />
        ) : (
          <ul className="nh-run-list" aria-label="Agent runs">
            {visible.map((run) => {
              const agent = agentPresentation(run.selected_agent);
              const outcome = OUTCOME_LABELS[run.outcome_status];
              const open = openRunId === run.id;
              return (
                <li key={run.id} className={`nh-run${open ? " is-open" : ""}`}>
                  <button
                    type="button"
                    className="nh-run__summary"
                    aria-expanded={open}
                    aria-controls={`run-${run.id}`}
                    onClick={() => setOpenRunId(open ? null : run.id)}
                  >
                    <span className={`nh-agent-chip nh-agent-chip--${agent.tone}`}>
                      <Icon name={agent.icon} size={14} />
                      {agent.short}
                    </span>
                    <span className="nh-run__text">
                      <span className="nh-run__message">“{run.user_message}”</span>
                      <span className="nh-run__meta">
                        {intentLabel(run.detected_intent)} · confidence {run.confidence.toFixed(2)} · {run.outcome_summary}
                      </span>
                    </span>
                    <span className="nh-run__side">
                      <Badge tone={outcome.tone}>{outcome.label}</Badge>
                      <time dateTime={run.created_at} title={formatTimestamp(run.created_at)}>
                        {formatRelative(run.created_at)}
                      </time>
                    </span>
                  </button>
                  {open && (
                    <div id={`run-${run.id}`} className="nh-run__detail">
                      <AgentTimeline run={run} />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
