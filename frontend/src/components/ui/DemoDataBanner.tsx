import { Icon } from "./Icon";

interface DemoDataBannerProps {
  message?: string;
}

/**
 * Persistent notice that everything shown is synthetic. Required so nobody
 * mistakes the prototype's departments, people or statuses for real ones.
 */
export function DemoDataBanner({
  message = "This is a demonstration prototype. The hospital, departments and people shown are fictional, and nothing here is medical advice.",
}: DemoDataBannerProps) {
  return (
    <div className="nh-demo-banner" role="note" aria-label="Demonstration data notice">
      <Icon name="info" size={18} />
      <p>
        <strong>Demo data.</strong> {message}
      </p>
    </div>
  );
}
