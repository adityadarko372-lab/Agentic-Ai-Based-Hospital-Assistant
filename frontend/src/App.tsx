import { MotionConfig } from "framer-motion";
import { Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { ToastProvider } from "./components/ui";
import { BackendHealthProvider } from "./hooks/BackendHealthContext";
import { DashboardPage } from "./pages/DashboardPage";
import { DesignSystemPage } from "./pages/DesignSystemPage";
import { ModulePreviewPage } from "./pages/ModulePreviewPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ServicesPage } from "./pages/ServicesPage";

/**
 * Route map. Modules not yet implemented render an honest preview page that
 * names the phase delivering them (see docs/first report.md).
 */
export default function App() {
  return (
    // reducedMotion="user" disables Framer Motion animations when the OS
    // "reduce motion" setting is on.
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <BackendHealthProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route
                path="assistant"
                element={
                  <ModulePreviewPage
                    eyebrow="Module 2 · AI Hospital Assistant"
                    title="AI Assistant"
                    description="Chat with Nova Health. A Supervisory Agent routes each request to the right specialist agent."
                    icon="chat"
                    plannedPhase="Phase 3"
                    plannedCapabilities={[
                      "Answer hospital questions such as which department to visit and what to bring",
                      "Route requests to the Patient Assistance, Appointment or Care Navigation agent",
                      "Show a live Agent Activity panel for every request",
                    ]}
                  />
                }
              />
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
              <Route
                path="appointments"
                element={
                  <ModulePreviewPage
                    eyebrow="Module 5 · Appointment Management"
                    title="Appointments"
                    description="Submit an appointment request and see its real status."
                    icon="calendar"
                    plannedPhase="Phase 2"
                    plannedCapabilities={[
                      "Form with patient name, department, preferred date and reason",
                      "Requests saved to the SQLite database with status Pending",
                      "A list of your requests that survives a page refresh",
                    ]}
                  />
                }
              />
              <Route path="services" element={<ServicesPage />} />
              <Route
                path="activity"
                element={
                  <ModulePreviewPage
                    eyebrow="Module 3 · Multi-Agent System"
                    title="Agent Activity"
                    description="A history of which agent handled each request and what happened."
                    icon="activity"
                    plannedPhase="Phase 3"
                    plannedCapabilities={[
                      "Supervisory Agent decision: detected intent, confidence and evidence",
                      "The specialist agent selected and the action it took",
                      "The real outcome, such as an appointment request reference",
                    ]}
                  />
                }
              />
              <Route path="design-system" element={<DesignSystemPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BackendHealthProvider>
      </ToastProvider>
    </MotionConfig>
  );
}
