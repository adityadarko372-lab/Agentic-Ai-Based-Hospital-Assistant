import type { IconName } from "../components/ui";
import type { UserRole } from "../services/types";

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  description: string;
}

/** Patient navigation. Each entry maps to one module in partial implementation.md. */
export const PRIMARY_NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: "home", description: "Your overview" },
  { to: "/assistant", label: "AI Assistant", icon: "chat", description: "Ask Nova Health" },
  {
    to: "/symptom-guidance",
    label: "Symptom Guidance",
    icon: "stethoscope",
    description: "Preliminary care navigation",
  },
  { to: "/appointments", label: "Appointments", icon: "calendar", description: "Requests and status" },
  { to: "/services", label: "Hospital Services", icon: "building", description: "Departments" },
  { to: "/activity", label: "Agent Activity", icon: "activity", description: "Who handled what" },
];

/** Phase 5: hospital front-desk staff navigation. */
export const STAFF_NAV: NavItem[] = [
  { to: "/front-desk", label: "Front Desk", icon: "shield", description: "Review appointment requests" },
  { to: "/services", label: "Hospital Services", icon: "building", description: "Departments" },
];

export const SECONDARY_NAV: NavItem[] = [
  { to: "/design-system", label: "Design System", icon: "layers", description: "UI components" },
];

export function navForRole(role: UserRole | undefined): NavItem[] {
  return role === "front_desk" ? STAFF_NAV : PRIMARY_NAV;
}

/** Where each role lands after signing in. */
export function homeForRole(role: UserRole | undefined): string {
  return role === "front_desk" ? "/front-desk" : "/";
}

/** Pages open to both roles. Everything else belongs to one role only. */
const SHARED_PATHS = ["/services", "/design-system"];

/**
 * Whether a role may open a path. Used to pick a safe post-login redirect;
 * the routes themselves are guarded by <RequireRole> and the backend checks
 * the role on every request.
 */
export function canAccessPath(role: UserRole | undefined, path: string): boolean {
  const pathname = path.split(/[?#]/)[0] || "/";
  if (SHARED_PATHS.some((shared) => pathname === shared || pathname.startsWith(`${shared}/`))) return true;
  const isStaffPath = pathname === "/front-desk" || pathname.startsWith("/front-desk/");
  return role === "front_desk" ? isStaffPath : !isStaffPath;
}
