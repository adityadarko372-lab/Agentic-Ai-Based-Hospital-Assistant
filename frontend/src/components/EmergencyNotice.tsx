import { Icon } from "./ui";

/**
 * Always-visible emergency guidance for India. 112 is the national emergency
 * number and 108 is the emergency ambulance service in most states.
 * Links use tel: so they can be tapped on a phone.
 */
export function EmergencyNotice() {
  return (
    <aside className="nh-emergency-notice" aria-label="Emergency information">
      <span className="nh-emergency-notice__icon">
        <Icon name="alert" size={20} />
      </span>
      <p>
        <strong>Medical emergency?</strong> Do not wait for this assistant. Call{" "}
        <a href="tel:112">112</a> (national emergency) or <a href="tel:108">108</a> (ambulance), or go
        to the nearest emergency department.
      </p>
    </aside>
  );
}
