import { Link } from "react-router-dom";

import { PageHeader } from "../components/layout/PageHeader";
import { Card, EmptyState } from "../components/ui";

export function NotFoundPage() {
  return (
    <div className="nh-page">
      <PageHeader title="Page not found" />
      <Card>
        <EmptyState
          icon="alert"
          title="We couldn't find that page"
          description="The link may be outdated. Use the menu or return to your dashboard."
          action={
            <Link to="/" className="nh-button nh-button--primary">
              Go to dashboard
            </Link>
          }
        />
      </Card>
    </div>
  );
}
