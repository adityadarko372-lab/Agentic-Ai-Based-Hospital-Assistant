import { Link, useLocation } from "react-router-dom";

import { Icon } from "../ui";

/** Floating "Ask Nova" button, available on every page except the assistant itself. */
export function AssistantFab() {
  const { pathname } = useLocation();
  if (pathname.startsWith("/assistant")) return null;

  return (
    <Link to="/assistant" className="nh-fab" aria-label="Open the AI Assistant">
      <Icon name="sparkle" size={22} />
      <span className="nh-fab__label">Ask Nova</span>
    </Link>
  );
}
