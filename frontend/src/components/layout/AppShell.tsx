import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useOutlet } from "react-router-dom";
import { motion } from "framer-motion";

import { PRIMARY_NAV, SECONDARY_NAV } from "../../config/navigation";
import { useBackendHealthContext } from "../../hooks/BackendHealthContext";
import { Button, Icon } from "../ui";
import { AssistantFab } from "./AssistantFab";
import { BackendStatus } from "./BackendStatus";
import { BrandLogo } from "./BrandLogo";
import { MobileDrawer } from "./MobileDrawer";
import { NavList } from "./NavList";

/**
 * Application frame: desktop sidebar, top bar (with the mobile menu button and
 * backend status), animated page area and the floating assistant button.
 */
export function AppShell() {
  const location = useLocation();
  const outlet = useOutlet();
  const { state } = useBackendHealthContext();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const isFirstRender = useRef(true);

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  // After client-side navigation, move focus to the main region so keyboard
  // and screen-reader users land on the new page instead of the old link.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    mainRef.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  return (
    <div className="nh-app">
      <a className="nh-skip-link" href="#nh-main">
        Skip to main content
      </a>

      <aside className="nh-sidebar" aria-label="Sidebar">
        <BrandLogo />
        <NavList items={PRIMARY_NAV} label="Main" />
        <div className="nh-sidebar__spacer" />
        <div className="nh-sidebar__divider" />
        <NavList items={SECONDARY_NAV} label="System" />
        <p className="nh-sidebar__footnote">
          Prototype · synthetic data only
        </p>
      </aside>

      <div className="nh-main-column">
        <header className="nh-topbar">
          <Button
            variant="secondary"
            iconOnly
            className="nh-topbar__menu"
            aria-label="Open menu"
            aria-expanded={drawerOpen}
            aria-controls="nh-mobile-drawer"
            onClick={() => setDrawerOpen(true)}
          >
            <Icon name="menu" />
          </Button>
          <div className="nh-topbar__brand">
            <BrandLogo />
          </div>
          <div className="nh-topbar__spacer" />
          <BackendStatus state={state} />
        </header>

        <main id="nh-main" ref={mainRef} className="nh-main" tabIndex={-1}>
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            {outlet}
          </motion.div>
        </main>
      </div>

      <MobileDrawer open={drawerOpen} onClose={closeDrawer} />
      <AssistantFab />
    </div>
  );
}
