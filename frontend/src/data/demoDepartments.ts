/**
 * FICTIONAL demonstration departments for the Nova Health prototype.
 *
 * These are placeholders for the Phase 1 visual shell only. In Phase 2 this
 * list moves to the backend (`backend/app/knowledge/hospital_info.json`) and is
 * loaded from `/api/hospital/departments`. No timings, phone numbers or staff
 * names are invented here.
 */
import type { IconName } from "../components/ui";

export interface DemoDepartment {
  id: string;
  name: string;
  summary: string;
  icon: IconName;
}

export const DEMO_DEPARTMENTS: DemoDepartment[] = [
  {
    id: "general-medicine",
    name: "General Medicine",
    summary: "First point of contact for common illnesses and general consultations.",
    icon: "stethoscope",
  },
  {
    id: "cardiology",
    name: "Cardiology",
    summary: "Heart and blood-vessel related consultations and follow-ups.",
    icon: "activity",
  },
  {
    id: "orthopaedics",
    name: "Orthopaedics",
    summary: "Bones, joints, muscles and injury-related care.",
    icon: "shield",
  },
  {
    id: "paediatrics",
    name: "Paediatrics",
    summary: "Healthcare for infants, children and adolescents.",
    icon: "sparkle",
  },
  {
    id: "dermatology",
    name: "Dermatology",
    summary: "Skin, hair and nail related consultations.",
    icon: "layers",
  },
  {
    id: "ent",
    name: "ENT",
    summary: "Ear, nose and throat consultations.",
    icon: "chat",
  },
];
