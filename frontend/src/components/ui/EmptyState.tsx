import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";

interface EmptyStateProps {
  icon?: IconName;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ icon = "layers", title, description, action }: EmptyStateProps) {
  return (
    <div className="nh-empty">
      <div className="nh-empty__icon">
        <Icon name={icon} size={26} />
      </div>
      <h3 className="nh-empty__title">{title}</h3>
      {description && <p className="nh-empty__description">{description}</p>}
      {action}
    </div>
  );
}
