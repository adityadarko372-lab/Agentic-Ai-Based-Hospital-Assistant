import type { ReactNode } from "react";

export type BadgeTone = "pending" | "confirmed" | "emergency" | "info" | "neutral";

interface BadgeProps {
  tone: BadgeTone;
  children: ReactNode;
}

/**
 * Status badge. Colour is never the only signal: every badge carries a text
 * label (e.g. "Pending"), which matters for colour-blind users.
 */
export function Badge({ tone, children }: BadgeProps) {
  return (
    <span className={`nh-badge nh-badge--${tone}`}>
      <span className="nh-badge__dot" aria-hidden="true" />
      {children}
    </span>
  );
}
