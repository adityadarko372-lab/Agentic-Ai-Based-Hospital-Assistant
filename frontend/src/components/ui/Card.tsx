import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./cx";

interface CardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  variant?: "raised" | "sunken" | "flat";
  interactive?: boolean;
  /** Render as a semantic element (section/article) when it groups content. */
  as?: "div" | "section" | "article";
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** Heading level for the title, to keep the page outline correct. */
  headingLevel?: 2 | 3;
}

export function Card({
  variant = "raised",
  interactive = false,
  as: Element = "div",
  title,
  subtitle,
  actions,
  headingLevel = 2,
  className,
  children,
  ...rest
}: CardProps) {
  const Heading = headingLevel === 2 ? "h2" : "h3";

  return (
    <Element
      className={cx(
        "nh-card",
        variant === "sunken" && "nh-card--sunken",
        variant === "flat" && "nh-card--flat",
        interactive && "nh-card--interactive",
        className,
      )}
      {...rest}
    >
      {(title || actions) && (
        <div className="nh-card__header">
          <div>
            {title && <Heading className="nh-card__title">{title}</Heading>}
            {subtitle && <p className="nh-card__subtitle">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </Element>
  );
}
