import { Link } from "react-router-dom";

import { PageHeader } from "../components/layout/PageHeader";
import { Badge, Button, Card, DemoDataBanner, Icon, Skeleton, type IconName } from "../components/ui";
import { useApiResource } from "../hooks/useApiResource";
import { hospitalApi } from "../services/novaApi";
import type { Department } from "../services/types";

function DepartmentCard({ department }: { department: Department }) {
  return (
    <Card as="article" variant="flat" className="nh-department-card">
      <div className="nh-department-card__head">
        <span className="nh-service-item__icon">
          <Icon name={department.icon as IconName} size={22} />
        </span>
        {department.accepts_appointments ? (
          <Badge tone="info">Appointment by request</Badge>
        ) : (
          <Badge tone="neutral">No appointment needed</Badge>
        )}
      </div>
      <h3 className="nh-department-card__name">{department.name}</h3>
      <p className="nh-department-card__summary">{department.summary}</p>
      <ul className="nh-department-card__facts">
        <li>
          <Icon name="mapPin" size={15} />
          {department.location}
        </li>
        <li>
          <Icon name="clock" size={15} />
          {department.opening_hours}
        </li>
        <li>
          <Icon name="phone" size={15} />
          {department.extension}
        </li>
      </ul>
      {department.accepts_appointments && (
        <Link
          to={`/appointments?department=${encodeURIComponent(department.id)}`}
          className="nh-button nh-button--secondary nh-button--sm nh-department-card__cta"
          aria-label={`Request appointment: ${department.name}`}
        >
          Request appointment
        </Link>
      )}
    </Card>
  );
}

/** Hospital services directory, loaded from the backend knowledge file. */
export function ServicesPage() {
  const departments = useApiResource(hospitalApi.departments);
  const info = useApiResource(hospitalApi.info);

  const clinical = (departments.data ?? []).filter((d) => d.category === "clinical");
  const services = (departments.data ?? []).filter((d) => d.category === "service");

  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Hospital services"
        title="Departments"
        description="Where to go, when it is open and whether you need an appointment."
      />
      <DemoDataBanner message="The hospital, departments, locations, timings and extensions are fictional sample content." />

      {info.data && (
        <Card as="section" title={info.data.hospital.name} subtitle={info.data.hospital.city}>
          <div className="nh-info-grid">
            <dl className="nh-status-list">
              <div>
                <dt>Outpatient (OPD) hours</dt>
                <dd>{info.data.hospital.opd_hours}</dd>
              </div>
              <div>
                <dt>Emergency</dt>
                <dd>{info.data.hospital.emergency_hours}</dd>
              </div>
              <div>
                <dt>Help desk</dt>
                <dd>{info.data.hospital.help_desk}</dd>
              </div>
              <div>
                <dt>Visiting hours</dt>
                <dd>{info.data.hospital.visiting_hours}</dd>
              </div>
            </dl>
            <div>
              <h3 className="nh-subheading">What to bring to your appointment</h3>
              <ul className="nh-checklist">
                {info.data.appointment_guidance.what_to_bring.map((item) => (
                  <li key={item}>
                    <Icon name="check" size={16} />
                    {item}
                  </li>
                ))}
              </ul>
              <p className="nh-field__hint nh-info-grid__note">{info.data.appointment_guidance.arrival_advice}</p>
            </div>
          </div>
        </Card>
      )}

      {departments.loading && !departments.data ? (
        <div className="nh-department-grid" role="status" aria-busy="true" aria-label="Loading departments">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} height={220} />
          ))}
        </div>
      ) : departments.error && !departments.data ? (
        <Card>
          <div className="nh-status-panel">
            <p>Departments could not be loaded: {departments.error}</p>
            <Button variant="secondary" size="sm" onClick={() => void departments.reload()}>
              Try again
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <section aria-labelledby="clinical-heading">
            <h2 id="clinical-heading" className="nh-section-title">
              Clinical departments
            </h2>
            <ul className="nh-department-grid">
              {clinical.map((department) => (
                <li key={department.id}>
                  <DepartmentCard department={department} />
                </li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="services-heading">
            <h2 id="services-heading" className="nh-section-title">
              Walk-in and emergency services
            </h2>
            <ul className="nh-department-grid">
              {services.map((department) => (
                <li key={department.id}>
                  <DepartmentCard department={department} />
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
