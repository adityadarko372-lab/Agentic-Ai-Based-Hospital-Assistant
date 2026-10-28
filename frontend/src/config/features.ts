import type { HealthResponse } from "../services/healthService";

type Features = HealthResponse["features"];

/** Lists only the optional Phase 5 features the server reports as switched on. */
export function describeAddOns(features: Features): string {
  const on: string[] = [];
  if (features.health_info_enabled) {
    on.push(features.health_info_index_present ? "Health information (MedQuAD)" : "Health information (index not built)");
  }
  if (features.llm_phrasing_enabled) on.push("AI rewording (local Ollama)");
  if (features.front_desk_enabled) on.push("Front-desk review");
  return on.length > 0 ? on.join(" · ") : "Off (not required)";
}

/** How messages are routed right now (the trained model falls back to rules). */
export function describeRouting(features: Features): string {
  if (features.intent_classifier_active !== "rules") return "Trained classifier (optional), rules as fallback";
  return features.intent_classifier === "transformer"
    ? "Transparent rules (trained model not installed)"
    : "Transparent rules (default)";
}
