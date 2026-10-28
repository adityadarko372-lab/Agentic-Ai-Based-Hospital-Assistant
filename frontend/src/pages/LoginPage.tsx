import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { EmergencyNotice } from "../components/EmergencyNotice";
import { BrandLogo } from "../components/layout/BrandLogo";
import { Button, Card, DemoDataBanner, Icon, SelectInput, TextInput } from "../components/ui";
import { canAccessPath, homeForRole } from "../config/navigation";
import { ApiError } from "../services/apiClient";
import type { UserRole } from "../services/types";

// Demo accounts seeded by backend/app/db/seed.py (documented in README).
// All data is synthetic; every account uses the same demo password.
const DEMO_PASSWORD = "NovaDemo@2026";

interface DemoAccount {
  email: string;
  name: string;
  role: UserRole;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { email: "patient@novahealth.demo", name: "Asha Verma", role: "patient" },
  { email: "aditya.singh@novahealth.demo", name: "Aditya Singh", role: "patient" },
  { email: "aaryan.naik@novahealth.demo", name: "Aaryan Naik", role: "patient" },
  { email: "bhavish.keni@novahealth.demo", name: "Bhavish Keni", role: "patient" },
  { email: "rohan.mehta@novahealth.demo", name: "Rohan Mehta", role: "patient" },
  { email: "kavya.iyer@novahealth.demo", name: "Kavya Iyer", role: "patient" },
  { email: "frontdesk@novahealth.demo", name: "Meera Desai", role: "front_desk" },
];

function roleLabel(role: UserRole): string {
  return role === "front_desk" ? "Front desk staff" : "Patient";
}

interface FieldErrors {
  email?: string;
  password?: string;
}

export function LoginPage() {
  const { status, user, signIn, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const requestedPath = (location.state as { from?: string } | null)?.from;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [demoEmail, setDemoEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  /** Go back to the page that asked for sign-in, if this role may open it. */
  function destinationFor(role: UserRole): string {
    return requestedPath && canAccessPath(role, requestedPath) ? requestedPath : homeForRole(role);
  }

  if (status === "signed_in" && user) return <Navigate to={destinationFor(user.role)} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const errors: FieldErrors = {};
    if (!email.trim()) errors.email = "Please enter your email address.";
    if (!password) errors.password = "Please enter your password.";
    setFieldErrors(errors);
    setFormError(null);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const signedIn = await signIn(email, password);
      navigate(destinationFor(signedIn.role), { replace: true });
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setFieldErrors(error.fieldErrors);
      } else {
        setFormError(error instanceof Error ? error.message : "Sign-in failed. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemoAccount() {
    setEmail(demoEmail);
    setPassword(DEMO_PASSWORD);
    setFieldErrors({});
    setFormError(null);
  }

  return (
    <div className="nh-login">
      <div className="nh-login__intro">
        <BrandLogo />
        <h1 className="nh-login__title">Your hospital assistant, in one calm place.</h1>
        <p className="nh-login__lead">
          Find the right department, request appointments and get cautious, preliminary care guidance,
          coordinated by a team of specialist AI agents.
        </p>
        <ul className="nh-checklist nh-login__points">
          <li>
            <Icon name="check" size={16} />
            Appointment requests saved with an honest status
          </li>
          <li>
            <Icon name="check" size={16} />
            Every assistant step is visible in the activity history
          </li>
          <li>
            <Icon name="check" size={16} />
            Urgent warning signs are always directed to emergency care
          </li>
        </ul>
      </div>

      <main className="nh-login__panel" id="nh-main">
        <Card as="section" className="nh-login__card" aria-labelledby="login-heading">
          <h2 id="login-heading" className="nh-login__heading">
            Sign in
          </h2>
          <p className="nh-card__subtitle">Choose a demo account below to explore the prototype.</p>

          {sessionExpired && (
            <p className="nh-inline-alert nh-inline-alert--warning" role="status">
              Your session ended. Please sign in again.
            </p>
          )}
          {formError && (
            <p className="nh-inline-alert nh-inline-alert--error" role="alert">
              <Icon name="alert" size={16} />
              {formError}
            </p>
          )}

          <form className="nh-stack nh-login__form" onSubmit={handleSubmit} noValidate>
            <TextInput
              label="Email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              error={fieldErrors.email}
              required
            />
            <TextInput
              label="Password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={fieldErrors.password}
              required
            />
            <Button type="submit" loading={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <div className="nh-demo-account">
            <div className="nh-demo-account__picker">
              <SelectInput
                label="Demo account"
                value={demoEmail}
                onChange={(event) => setDemoEmail(event.target.value)}
              >
                {DEMO_ACCOUNTS.map((account) => (
                  <option key={account.email} value={account.email}>
                    {account.name} · {roleLabel(account.role)} · {account.email}
                  </option>
                ))}
              </SelectInput>
            </div>
            <Button variant="secondary" size="sm" onClick={fillDemoAccount}>
              Fill in
            </Button>
          </div>
          <p className="nh-demo-account__detail nh-demo-account__password">
            Every demo account uses the password {DEMO_PASSWORD}
          </p>
        </Card>
        <DemoDataBanner message="Accounts are fictional. This demo login is not production-grade security." />
        <EmergencyNotice />
      </main>
    </div>
  );
}
