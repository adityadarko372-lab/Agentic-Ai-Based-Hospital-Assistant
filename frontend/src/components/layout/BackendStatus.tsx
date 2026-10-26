import type { ConnectionState } from "../../hooks/useBackendHealth";

const LABELS: Record<ConnectionState, string> = {
  checking: "Checking backend…",
  online: "Backend connected",
  offline: "Backend offline",
};

interface BackendStatusProps {
  state: ConnectionState;
}

/** Live connection indicator, announced politely to screen readers. */
export function BackendStatus({ state }: BackendStatusProps) {
  return (
    <span className={`nh-status nh-status--${state}`} role="status" aria-live="polite">
      <span className="nh-status__dot" aria-hidden="true" />
      <span className="nh-status__label">{LABELS[state]}</span>
    </span>
  );
}
