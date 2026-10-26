import { createContext, useContext, type ReactNode } from "react";

import { useBackendHealth } from "./useBackendHealth";

type BackendHealthValue = ReturnType<typeof useBackendHealth>;

const BackendHealthContext = createContext<BackendHealthValue | null>(null);

/** Shares one health poller across the whole app (top bar, dashboard, etc.). */
export function BackendHealthProvider({ children }: { children: ReactNode }) {
  const value = useBackendHealth();
  return <BackendHealthContext.Provider value={value}>{children}</BackendHealthContext.Provider>;
}

export function useBackendHealthContext(): BackendHealthValue {
  const context = useContext(BackendHealthContext);
  if (!context) {
    throw new Error("useBackendHealthContext must be used inside <BackendHealthProvider>");
  }
  return context;
}
