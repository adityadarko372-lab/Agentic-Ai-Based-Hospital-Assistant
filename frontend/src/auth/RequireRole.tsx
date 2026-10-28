import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { homeForRole } from "../config/navigation";
import type { UserRole } from "../services/types";
import { useAuth } from "./AuthContext";

/**
 * Shows its children only to the given role and sends anyone else to their
 * own home page. This is a convenience for the UI; the backend enforces the
 * same rule on every endpoint.
 */
export function RequireRole({ role, children }: { role: UserRole; children: ReactNode }) {
  const { user } = useAuth();
  if (user && user.role !== role) return <Navigate to={homeForRole(user.role)} replace />;
  return <>{children}</>;
}
