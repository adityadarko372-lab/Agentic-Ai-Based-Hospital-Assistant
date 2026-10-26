import { NavLink } from "react-router-dom";

import type { NavItem } from "../../config/navigation";
import { Icon } from "../ui";

interface NavListProps {
  items: NavItem[];
  label: string;
  onNavigate?: () => void;
}

/** Vertical navigation list; the active route gets aria-current="page". */
export function NavList({ items, label, onNavigate }: NavListProps) {
  return (
    <nav aria-label={label}>
      <ul className="nh-nav">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `nh-nav__link${isActive ? " is-active" : ""}`}
              onClick={onNavigate}
            >
              <span className="nh-nav__icon">
                <Icon name={item.icon} size={19} />
              </span>
              <span className="nh-nav__text">
                <span className="nh-nav__label">{item.label}</span>
                <span className="nh-nav__description">{item.description}</span>
              </span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
