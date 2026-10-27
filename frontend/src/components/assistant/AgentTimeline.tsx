import { ACTION_LABELS, agentPresentation, intentLabel, OUTCOME_LABELS } from "../../config/agents";
import type { AgentRun, AgentStep } from "../../services/types";
import { formatTimestamp } from "../../utils/dates";
import { Badge, Icon } from "../ui";

const STATUS_ICON = { ok: "check", warning: "alert", blocked: "shield", fallback: "refresh", error: "alert" } as const;

function StepExtras({ step }: { step: AgentStep }) {
  const evidence = step.action === "classify_intent" ? (step.data.evidence as string[] | undefined) : undefined;
  const reasons = step.action === "apply_care_rules" ? (step.data.reasons as string[] | undefined) : undefined;
  if (evidence?.length) {
    return (
      <ul className="nh-evidence" aria-label="Matched evidence">
        {evidence.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    );
  }
  if (reasons?.length) {
    return (
      <ul className="nh-timeline__reasons">
        {reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    );
  }
  return null;
}

interface AgentTimelineProps {
  run: AgentRun;
  /** Hide the patient's own message (e.g. when shown next to the chat). */
  showMessage?: boolean;
}

/**
 * Visual trace of one request: which agent did what, in order, and the
 * real outcome. Mirrors the agent_runs / agent_steps tables.
 */
export function AgentTimeline({ run, showMessage = false }: AgentTimelineProps) {
  const selected = agentPresentation(run.selected_agent);
  const outcome = OUTCOME_LABELS[run.outcome_status];
  const confidencePercent = Math.round(run.confidence * 100);

  return (
    <div className="nh-trace">
      <dl className="nh-trace__summary">
        <div>
          <dt>Handled by</dt>
          <dd>
            <span className={`nh-agent-chip nh-agent-chip--${selected.tone}`}>
              <Icon name={selected.icon} size={14} />
              {run.selected_agent}
            </span>
          </dd>
        </div>
        <div>
          <dt>Intent</dt>
          <dd className="nh-trace__intent">{intentLabel(run.detected_intent)}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>
            <span className="nh-confidence" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={confidencePercent} aria-label="Routing confidence">
              <span className="nh-confidence__bar" style={{ width: `${confidencePercent}%` }} />
            </span>
            <span className="nh-trace__number">
              {run.confidence.toFixed(2)} · {run.classifier_method}
            </span>
          </dd>
        </div>
        <div>
          <dt>Outcome</dt>
          <dd>
            <Badge tone={outcome.tone}>{outcome.label}</Badge>
            {run.reference && <span className="nh-trace__reference">{run.reference}</span>}
          </dd>
        </div>
      </dl>
      {showMessage && <p className="nh-trace__message">“{run.user_message}”</p>}

      <ol className="nh-timeline" aria-label="Agent steps">
        {run.steps.map((step) => {
          const agent = agentPresentation(step.agent);
          return (
            <li key={step.order} className={`nh-timeline__step nh-timeline__step--${step.status}`}>
              <span className={`nh-timeline__dot nh-agent-chip--${agent.tone}`} aria-hidden="true">
                <Icon name={agent.icon} size={13} />
              </span>
              <div className="nh-timeline__body">
                <p className="nh-timeline__title">
                  <span className="nh-timeline__agent">{agent.short}</span>
                  {ACTION_LABELS[step.action] ?? step.action}
                  {step.status !== "ok" && (
                    <span className={`nh-timeline__status nh-timeline__status--${step.status}`}>
                      <Icon name={STATUS_ICON[step.status]} size={12} />
                      {step.status}
                    </span>
                  )}
                </p>
                <p className="nh-timeline__detail">{step.detail}</p>
                <StepExtras step={step} />
              </div>
            </li>
          );
        })}
      </ol>
      <p className="nh-trace__footer">
        {run.steps.length} steps · {run.duration_ms} ms · {formatTimestamp(run.created_at)}
      </p>
    </div>
  );
}
