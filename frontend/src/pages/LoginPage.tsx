import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { EmergencyNotice } from "../components/EmergencyNotice";
import { BrandLogo } from "../components/layout/BrandLogo";
import { Button, Card, DemoDataBanner, Icon, TextInput } from "../components/ui";
import { ApiError } from "../services/apiClient";

// Fictional demo account (documented in README). Not a real person.
const DEMO_EMAIL = "patient@novahealth.demo";
const DEMO_PASSWORD = "NovaDemo@2026";

interface FieldErrors {
  email?: string;
  password?: string;
}

export function LoginPage() {
  const { status, signIn, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "signed_in") return <Navigate to={redirectTo} replace />;

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
      await signIn(email, password);
      navigate(redirectTo, { replace: true });
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

  function useDemoAccount() {
    setEmail(DEMO_EMAIL);
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
          <p className="nh-card__subtitle">Use the demo patient account to explore the prototype.</p>

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
            <div>
              <p className="nh-demo-account__title">Demo patient account</p>
              <p className="nh-demo-account__detail">
                {DEMO_EMAIL} · {DEMO_PASSWORD}
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={useDemoAccount}>
              Fill in
            </Button>
          </div>
        </Card>
        <DemoDataBanner message="Accounts are fictional. This demo login is not production-grade security." />
        <EmergencyNotice />
      </main>
    </div>
  );
}
