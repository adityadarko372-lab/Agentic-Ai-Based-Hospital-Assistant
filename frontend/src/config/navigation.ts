import type { IconName } from "../components/ui";

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  description: string;
}

/** Main navigation. Each entry maps to one module in partial implementation.md. */
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

export const SECONDARY_NAV: NavItem[] = [
  { to: "/design-system", label: "Design System", icon: "layers", description: "UI components" },
];
