interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
}

/** Loading placeholder. Hidden from assistive tech; pair with an aria-busy region. */
export function Skeleton({ width = "100%", height = 16, className }: SkeletonProps) {
  return (
    <span
      className={["nh-skeleton", className].filter(Boolean).join(" ")}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
