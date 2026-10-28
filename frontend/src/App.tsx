import { MotionConfig } from "framer-motion";
import { Outlet, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { RequireRole } from "./auth/RequireRole";
import { AppShell } from "./components/layout/AppShell";
import { ToastProvider } from "./components/ui";
import { BackendHealthProvider } from "./hooks/BackendHealthContext";
import { AgentActivityPage } from "./pages/AgentActivityPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { AssistantPage } from "./pages/AssistantPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { DesignSystemPage } from "./pages/DesignSystemPage";
import { FrontDeskPage } from "./pages/FrontDeskPage";
import { SymptomGuidancePage } from "./pages/SymptomGuidancePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ServicesPage } from "./pages/ServicesPage";

/**
 * Route map. /login is public; every other page needs a signed-in user.
 * All five modules of partial implementation.md are patient routes; the
 * optional Phase 5 front desk is a staff route.
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
              {/* Patient modules. Staff are redirected to their own home. */}
              <Route
                element={
                  <RequireRole role="patient">
                    <Outlet />
                  </RequireRole>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="assistant" element={<AssistantPage />} />
                <Route path="symptom-guidance" element={<SymptomGuidancePage />} />
                <Route path="appointments" element={<AppointmentsPage />} />
                <Route path="activity" element={<AgentActivityPage />} />
              </Route>
              {/* Phase 5 staff workflow. */}
              <Route
                path="front-desk"
                element={
                  <RequireRole role="front_desk">
                    <FrontDeskPage />
                  </RequireRole>
                }
              />
              <Route path="services" element={<ServicesPage />} />
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
