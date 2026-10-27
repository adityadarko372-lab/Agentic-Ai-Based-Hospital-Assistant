import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./AuthContext";

/** Shows its children only to a signed-in user; otherwise redirects to /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return (
      <div className="nh-fullpage-loader" role="status" aria-live="polite">
        <span className="nh-button__spinner" aria-hidden="true" />
        Restoring your session…
      </div>
    );
  }

  if (status === "signed_out") {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }

  return <>{children}</>;
}
