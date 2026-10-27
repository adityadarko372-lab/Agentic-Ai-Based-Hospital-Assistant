import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { AppointmentForm } from "../components/appointments/AppointmentForm";
import { AppointmentRequestList } from "../components/appointments/AppointmentRequestList";
import { PageHeader } from "../components/layout/PageHeader";
import { Button, Card, DemoDataBanner, Icon, Skeleton, useToast } from "../components/ui";
import { useApiResource } from "../hooks/useApiResource";
import { appointmentApi, hospitalApi } from "../services/novaApi";
import type { AppointmentRequest } from "../services/types";

/** Module 5: Appointment Management. */
export function AppointmentsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
  const departments = useApiResource(hospitalApi.departments);
  const requests = useApiResource(appointmentApi.mine);

  const handleSubmitted = useCallback(
    (appointment: AppointmentRequest) => {
      showToast({
        tone: "success",
        title: `Request ${appointment.reference} saved`,
        message: "Status: Pending, awaiting hospital review.",
      });
      void requests.reload();
    },
    [requests, showToast],
  );

  const handleCancel = useCallback(
    async (reference: string) => {
      try {
        await appointmentApi.cancel(reference);
        showToast({ tone: "info", title: `Request ${reference} cancelled` });
      } catch (error) {
        showToast({
          tone: "error",
          title: "Could not cancel the request",
          message: error instanceof Error ? error.message : undefined,
        });
      } finally {
        await requests.reload();
      }
    },
    [requests, showToast],
  );

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Module 5 · Appointment Management"
        title="Appointments"
        description="Submit an appointment request and follow its real status. Requests stay Pending until the hospital reviews them."
      />
      <DemoDataBanner message="Requests are saved in the local demo database. No real hospital scheduling system is connected, so nothing is confirmed automatically." />

      <div className="nh-appointments-layout">
        <Card as="section" title="Request an appointment" subtitle="All fields are required.">
          {departments.loading && !departments.data ? (
            <div className="nh-stack" aria-busy="true" aria-label="Loading departments">
              <Skeleton height={46} />
              <Skeleton height={46} />
              <Skeleton height={46} />
              <Skeleton height={112} />
            </div>
          ) : departments.error || !departments.data ? (
            <div className="nh-status-panel">
              <p>Departments could not be loaded: {departments.error}</p>
              <Button variant="secondary" size="sm" onClick={() => void departments.reload()}>
                Try again
              </Button>
            </div>
          ) : (
            <AppointmentForm
              departments={departments.data}
              defaultPatientName={user?.full_name ?? ""}
              initialDepartmentId={searchParams.get("department") ?? ""}
              onSubmitted={handleSubmitted}
            />
          )}
        </Card>

        <Card
          as="section"
          title="My requests"
          subtitle="Newest first. Saved in the database, so they remain after a refresh."
          actions={
            <Button
              variant="secondary"
              size="sm"
              leadingIcon={<Icon name="refresh" size={14} />}
              onClick={() => void requests.reload()}
              loading={requests.loading && requests.data !== null}
            >
              Refresh
            </Button>
          }
        >
          {requests.loading && !requests.data ? (
            <div className="nh-stack" aria-busy="true" aria-label="Loading your requests">
              <Skeleton height={90} />
              <Skeleton height={90} />
            </div>
          ) : requests.error && !requests.data ? (
            <div className="nh-status-panel">
              <p>Your requests could not be loaded: {requests.error}</p>
              <Button variant="secondary" size="sm" onClick={() => void requests.reload()}>
                Try again
              </Button>
            </div>
          ) : (
            <AppointmentRequestList requests={requests.data ?? []} onCancel={handleCancel} />
          )}
        </Card>
      </div>
    </div>
  );
}
