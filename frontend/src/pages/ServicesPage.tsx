import { PageHeader } from "../components/layout/PageHeader";
import { Card, DemoDataBanner, Icon } from "../components/ui";
import { DEMO_DEPARTMENTS } from "../data/demoDepartments";

export function ServicesPage() {
  return (
    <div className="nh-page">
      <PageHeader
        eyebrow="Hospital services"
        title="Departments"
        description="An overview of the departments in the fictional Nova Health Multi-Speciality Hospital."
      />
      <DemoDataBanner message="These departments are sample content. Timings, locations and contact details are added from the backend directory in Phase 2." />

      <ul className="nh-department-grid">
        {DEMO_DEPARTMENTS.map((department) => (
          <li key={department.id}>
            <Card as="article" variant="flat" className="nh-department-card">
              <span className="nh-service-item__icon">
                <Icon name={department.icon} size={22} />
              </span>
              <h2 className="nh-department-card__name">{department.name}</h2>
              <p className="nh-department-card__summary">{department.summary}</p>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
