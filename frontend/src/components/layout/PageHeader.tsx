import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}

/** Consistent page heading. Every page has exactly one <h1>. */
export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <header className="nh-page-header">
      <div>
        {eyebrow && <p className="nh-page-header__eyebrow">{eyebrow}</p>}
        <h1 className="nh-page-header__title">{title}</h1>
        {description && <p className="nh-page-header__description">{description}</p>}
      </div>
      {actions && <div className="nh-page-header__actions">{actions}</div>}
    </header>
  );
}
