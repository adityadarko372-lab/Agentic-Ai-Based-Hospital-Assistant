import { useId } from "react";
import { Link } from "react-router-dom";

interface BrandLogoProps {
  compact?: boolean;
}

/** Nova Health wordmark with its cross-and-star mark. Links to the dashboard. */
export function BrandLogo({ compact = false }: BrandLogoProps) {
  // Each logo instance needs its own gradient id: the sidebar copy is
  // display:none on mobile, and a gradient defined inside a hidden SVG does
  // not render for other SVGs that reference the same id.
  const gradientId = `nh-brand-gradient-${useId().replace(/:/g, "")}`;

  return (
    // The accessible name starts with the visible words (WCAG 2.5.3 "Label in Name").
    <Link to="/" className="nh-brand" aria-label={compact ? "Nova Health, go to dashboard" : undefined}>
      <svg className="nh-brand__mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#12908e" />
            <stop offset="1" stopColor="#085656" />
          </linearGradient>
        </defs>
        <rect width="48" height="48" rx="14" fill={`url(#${gradientId})`} />
        <path d="M20 12h8v8h8v8h-8v8h-8v-8h-8v-8h8z" fill="#fff" opacity="0.95" />
        <circle cx="36" cy="12" r="3" fill="#bfe7e3" />
      </svg>
      {!compact && (
        <span className="nh-brand__text">
          <span className="nh-brand__name">Nova Health</span>
          <span className="nh-brand__tagline"> Hospital Assistant</span>
          <span className="nh-visually-hidden">, go to dashboard</span>
        </span>
      )}
    </Link>
  );
}
