import { apiGet } from "./apiClient";

/** Shape of GET /api/health (mirrors backend/app/api/health.py). */
export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  demo_data: boolean;
  server_time: string;
  features: {
    intent_classifier: "rules" | "transformer";
    health_info_enabled: boolean;
    llm_phrasing_enabled: boolean;
    front_desk_enabled: boolean;
  };
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/api/health", 5000);
}
