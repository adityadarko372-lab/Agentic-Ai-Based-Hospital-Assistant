import { MotionConfig } from "framer-motion";
import { Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./components/layout/AppShell";
import { ToastProvider } from "./components/ui";
import { BackendHealthProvider } from "./hooks/BackendHealthContext";
import { AgentActivityPage } from "./pages/AgentActivityPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { AssistantPage } from "./pages/AssistantPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { DesignSystemPage } from "./pages/DesignSystemPage";
import { ModulePreviewPage } from "./pages/ModulePreviewPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ServicesPage } from "./pages/ServicesPage";

/**
 * Route map. /login is public; every other page needs a signed-in demo
 * patient. Modules not yet implemented render an honest preview page that
 * names the phase delivering them (see docs/first report.md).
 */
export default function App() {
  return (
    // reducedMotion="user" disables Framer Motion animations when the OS
    // "reduce motion" setting is on.
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <BackendHealthProvider>
          <AuthProvider>
          <Routes>
            <Route path="login" element={<LoginPage />} />
            <Route
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="assistant" element={<AssistantPage />} />
              <Route
                path="symptom-guidance"
                element={
                  <ModulePreviewPage
                    eyebrow="Module 4 · Preliminary Symptom Guidance"
                    title="Symptom Guidance"
                    description="A short questionnaire that suggests an appropriate next step. It does not diagnose."
                    icon="stethoscope"
                    plannedPhase="Phase 4"
                    plannedCapabilities={[
                      "Collect symptoms, duration and general information",
                      "Show emergency guidance (112 / 108) immediately for warning signs",
                      "Suggest a level of care and a relevant department, never a diagnosis",
                    ]}
                  />
                }
              />
              <Route path="appointments" element={<AppointmentsPage />} />
              <Route path="services" element={<ServicesPage />} />
              <Route path="activity" element={<AgentActivityPage />} />
              <Route path="design-system" element={<DesignSystemPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
          </AuthProvider>
        </BackendHealthProvider>
      </ToastProvider>
    </MotionConfig>
  );
}
