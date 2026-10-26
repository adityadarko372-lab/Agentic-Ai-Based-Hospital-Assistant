import { useCallback, useEffect, useRef, useState } from "react";

import { fetchHealth, type HealthResponse } from "../services/healthService";

export type ConnectionState = "checking" | "online" | "offline";

interface BackendHealth {
  state: ConnectionState;
  health: HealthResponse | null;
  errorMessage: string | null;
  lastCheckedAt: Date | null;
  recheck: () => void;
}

/**
 * Polls GET /api/health so the UI can honestly show whether the backend is
 * reachable. The interval is modest (20 s) to avoid noisy network traffic.
 */
export function useBackendHealth(pollIntervalMs = 20000): BackendHealth {
  const [state, setState] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);
  const isMounted = useRef(true);

  const check = useCallback(async () => {
    try {
      const result = await fetchHealth();
      if (!isMounted.current) return;
      setHealth(result);
      setState("online");
      setErrorMessage(null);
    } catch (error) {
      if (!isMounted.current) return;
      setState("offline");
      setErrorMessage(error instanceof Error ? error.message : "Unknown error");
    } finally {
      if (isMounted.current) setLastCheckedAt(new Date());
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    void check();
    const intervalId = window.setInterval(() => void check(), pollIntervalMs);
    return () => {
      isMounted.current = false;
      window.clearInterval(intervalId);
    };
  }, [check, pollIntervalMs]);

  const recheck = useCallback(() => {
    setState("checking");
    void check();
  }, [check]);

  return { state, health, errorMessage, lastCheckedAt, recheck };
}
