"use client";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, ApiError } from "@/lib/api";

/*
  Storage policy (matters for the threat model):

    session_token  → React state ONLY. Never written to localStorage,
                     sessionStorage, or cookies. An XSS payload that
                     reads window.localStorage gets nothing useful, so
                     it cannot impersonate the citizen on /reports,
                     /wallet/*, etc.

    pseudonymous_token (PT)
                   → React state AND localStorage (key below). PT is
                     itself an HMAC-SHA256 of the national_id keyed by
                     PT_SALT — there is no inverse function from PT
                     back to national_id. Reading the cached PT lets
                     the UI show "Welcome back, you were last logged
                     in as ◆◆◆◆XXXX, please re-enter your mnemonic"
                     without needing to keep the bearer alive across
                     page reloads.

    mnemonic       → never stored anywhere on the client. Cleared from
                     state the moment recover() resolves; the in-memory
                     React form state for the input is dropped when
                     SecureLogin unmounts.
*/

const PT_STORAGE_KEY = "integrity_shield.pt.v1";

interface RecoverResponse {
  pseudonymous_token: string;
  session_token: string;
  expires_at: string;
}

interface AuthState {
  pt: string | null;
  sessionToken: string | null;
  expiresAt: string | null;
}

export interface AuthContextValue extends AuthState {
  /** True when we hold a live bearer in memory. */
  isAuthenticated: boolean;
  /** True when we have a remembered PT but no live bearer (post-refresh). */
  hasCachedIdentity: boolean;
  /** Run /auth/recover; on success update both PT and session token. */
  recover: (nationalId: string, mnemonic: string) => Promise<void>;
  /** Drop bearer + cached PT. */
  logout: () => void;
  /** Drop bearer only (keep cached PT so UI can offer "log back in"). */
  expireSession: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    pt: null,
    sessionToken: null,
    expiresAt: null,
  });

  // Restore the cached PT (NOT the session token) on first mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const cached = window.localStorage.getItem(PT_STORAGE_KEY);
      if (cached && /^[0-9a-f]{64}$/i.test(cached)) {
        setState((s) => ({ ...s, pt: cached }));
      }
    } catch {
      // localStorage may be disabled (private mode, embedded contexts).
    }
  }, []);

  // If the bearer's expiry passes while the tab is open, drop it.
  useEffect(() => {
    if (!state.expiresAt || !state.sessionToken) return;
    const ms = new Date(state.expiresAt).getTime() - Date.now();
    if (ms <= 0) {
      setState((s) => ({ ...s, sessionToken: null, expiresAt: null }));
      return;
    }
    const t = setTimeout(() => {
      setState((s) => ({ ...s, sessionToken: null, expiresAt: null }));
    }, ms);
    return () => clearTimeout(t);
  }, [state.expiresAt, state.sessionToken]);

  const recover = useCallback(async (nationalId: string, mnemonic: string) => {
    const res = await api<RecoverResponse>("/auth/recover", {
      method: "POST",
      body: JSON.stringify({
        national_id: nationalId,
        mnemonic,
      }),
    });

    setState({
      pt: res.pseudonymous_token,
      sessionToken: res.session_token,
      expiresAt: res.expires_at,
    });

    try {
      window.localStorage.setItem(PT_STORAGE_KEY, res.pseudonymous_token);
    } catch {
      // localStorage write failures are non-fatal; auth still works for the tab.
    }
  }, []);

  const logout = useCallback(() => {
    setState({ pt: null, sessionToken: null, expiresAt: null });
    try {
      window.localStorage.removeItem(PT_STORAGE_KEY);
    } catch {
      /* noop */
    }
  }, []);

  const expireSession = useCallback(() => {
    setState((s) => ({ ...s, sessionToken: null, expiresAt: null }));
  }, []);

  const value: AuthContextValue = {
    pt: state.pt,
    sessionToken: state.sessionToken,
    expiresAt: state.expiresAt,
    isAuthenticated: !!state.sessionToken,
    hasCachedIdentity: !!state.pt && !state.sessionToken,
    recover,
    logout,
    expireSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }
  return ctx;
}

/**
 * Anyone making an authenticated API call should pull the bearer from this
 * hook so it follows session expiry. Returns null when no live bearer.
 */
export function useBearerHeaders(): Record<string, string> {
  const { sessionToken } = useAuth();
  return sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {};
}
