import { Link } from "react-router-dom";

import { PageHeader } from "../components/layout/PageHeader";
import { Badge, Card, DemoDataBanner, EmptyState, Icon, type IconName } from "../components/ui";

interface ModulePreviewPageProps {
  eyebrow: string;
  title: string;
  description: string;
  icon: IconName;
  plannedPhase: string;
  plannedCapabilities: string[];
}

/**
 * Honest placeholder for a module that is not built yet. It states which
 * phase delivers it instead of showing fake, non-working controls.
 */
export function ModulePreviewPage({
  eyebrow,
  title,
  description,
  icon,
  plannedPhase,
  plannedCapabilities,
}: ModulePreviewPageProps) {
  return (
    <div className="nh-page">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <DemoDataBanner />

      <Card as="section" title="Module status" actions={<Badge tone="info">{plannedPhase}</Badge>}>
        <EmptyState
          icon={icon}
          title="Not built yet"
          description={`This page is part of the navigation shell. Its working functionality is delivered in ${plannedPhase}.`}
          action={
            <Link to="/" className="nh-button nh-button--secondary nh-button--sm">
              Back to dashboard
            </Link>
          }
        />
        <h3 className="nh-subheading">What this module will do</h3>
        <ul className="nh-checklist">
          {plannedCapabilities.map((capability) => (
            <li key={capability}>
              <Icon name="check" size={16} />
              {capability}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
