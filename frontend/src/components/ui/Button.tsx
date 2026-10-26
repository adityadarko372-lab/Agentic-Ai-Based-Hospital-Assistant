import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { cx } from "./cx";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "md" | "sm";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner, disables the button and announces "busy" to screen readers. */
  loading?: boolean;
  iconOnly?: boolean;
  leadingIcon?: ReactNode;
}

/**
 * Neumorphic button. Defaults to type="button" so it never submits a form by
 * accident; pass type="submit" explicitly inside forms.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    iconOnly = false,
    leadingIcon,
    disabled,
    className,
    children,
    type = "button",
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(
        "nh-button",
        `nh-button--${variant}`,
        size === "sm" && "nh-button--sm",
        iconOnly && "nh-button--icon",
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className="nh-button__spinner" aria-hidden="true" /> : leadingIcon}
      {children}
    </button>
  );
});
