import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { setAuthToken, setUnauthorizedHandler } from "../services/apiClient";
import { authApi } from "../services/novaApi";
import type { User } from "../services/types";

/**
 * Demo session handling.
 *
 * The signed token is kept in sessionStorage: it survives a page refresh but
 * is cleared when the browser tab closes. The backend re-checks the token on
 * every request, so the UI is never the security boundary.
 */

export const SESSION_STORAGE_KEY = "nova_health_session";

type AuthStatus = "checking" | "signed_out" | "signed_in";

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  /** True when the user was signed out because the session expired. */
  sessionExpired: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredToken(): string | null {
  try {
    return window.sessionStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string | null): void {
  try {
    if (token) window.sessionStorage.setItem(SESSION_STORAGE_KEY, token);
    else window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private mode); the session then lasts until refresh.
  }
  setAuthToken(token);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>(() => (readStoredToken() ? "checking" : "signed_out"));
  const [user, setUser] = useState<User | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const signOut = useCallback(() => {
    storeToken(null);
    setUser(null);
    setStatus("signed_out");
  }, []);

  // Any 401 from a protected endpoint means the session is gone.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSessionExpired(true);
      signOut();
    });
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  // On first load, check that a stored token is still valid.
  useEffect(() => {
    const token = readStoredToken();
    if (!token) return;
    setAuthToken(token);
    let cancelled = false;
    authApi
      .me()
      .then((profile) => {
        if (cancelled) return;
        setUser(profile);
        setStatus("signed_in");
      })
      .catch(() => {
        if (!cancelled) signOut();
      });
    return () => {
      cancelled = true;
    };
  }, [signOut]);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    storeToken(result.access_token);
    setUser(result.user);
    setSessionExpired(false);
    setStatus("signed_in");
  }, []);

  const value = useMemo(
    () => ({ status, user, sessionExpired, signIn, signOut }),
    [status, user, sessionExpired, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
