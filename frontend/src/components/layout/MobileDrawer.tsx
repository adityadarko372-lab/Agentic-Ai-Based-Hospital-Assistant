import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { SECONDARY_NAV, type NavItem } from "../../config/navigation";
import { Button, Icon } from "../ui";
import { BrandLogo } from "./BrandLogo";
import { NavList } from "./NavList";

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
  items: NavItem[];
}

/**
 * Slide-in navigation for small screens. Behaves like a modal dialog:
 * Escape closes it, focus moves inside on open, and the page behind is inert
 * to scrolling.
 */
export function MobileDrawer({ open, onClose, items }: MobileDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.querySelector<HTMLElement>("a, button")?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="nh-drawer-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) onClose();
          }}
        >
          <motion.div
            ref={panelRef}
            id="nh-mobile-drawer"
            className="nh-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Main menu"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "tween", duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="nh-drawer__header">
              <BrandLogo />
              <Button variant="ghost" iconOnly aria-label="Close menu" onClick={onClose}>
                <Icon name="close" />
              </Button>
            </div>
            <NavList items={items} label="Main" onNavigate={onClose} />
            <div className="nh-sidebar__divider" />
            <NavList items={SECONDARY_NAV} label="System" onNavigate={onClose} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
