import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import { Button, Icon } from "../ui";

/** Signed-in user's name and a sign-out button, shown in the top bar. */
export function UserMenu() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  const initials = user.full_name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="nh-user-menu">
      <span className="nh-user-menu__avatar" aria-hidden="true">
        {initials}
      </span>
      <span className="nh-user-menu__text">
        <span className="nh-user-menu__name">{user.full_name}</span>
        <span className="nh-user-menu__role">Demo patient</span>
      </span>
      <Button
        variant="ghost"
        size="sm"
        iconOnly
        aria-label="Sign out"
        title="Sign out"
        onClick={() => {
          signOut();
          navigate("/login", { replace: true });
        }}
      >
        <Icon name="logout" size={18} />
      </Button>
    </div>
  );
}
