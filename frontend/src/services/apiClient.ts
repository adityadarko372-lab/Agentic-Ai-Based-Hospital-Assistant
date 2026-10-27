/**
 * Typed HTTP client for the Nova Health API.
 *
 * - All calls go to relative `/api/...` URLs (Vite proxies them to FastAPI).
 * - The session token (if any) is attached as `Authorization: Bearer ...`.
 * - Every request has a timeout so the UI never hangs on a dead backend.
 * - Failures become an `ApiError` with a friendly message and, for form
 *   validation failures, a per-field `fieldErrors` map from the backend.
 */

export class ApiError extends Error {
  readonly status: number | null;
  readonly fieldErrors: Record<string, string>;

  constructor(message: string, status: number | null, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

const DEFAULT_TIMEOUT_MS = 8000;

let authToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

/** Called by the auth context whenever the user signs in or out. */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Registers what to do when the server says the session is no longer valid. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

interface RequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
  /** Set false for the login call, whose 401 means "wrong password", not "session expired". */
  notifyOnUnauthorized?: boolean;
}

async function readErrorBody(response: Response): Promise<{ detail?: unknown; field_errors?: Record<string, string> }> {
  try {
    return (await response.json()) as { detail?: unknown; field_errors?: Record<string, string> };
  } catch {
    return {};
  }
}

export async function apiRequest<T>(method: "GET" | "POST", path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers = {}, timeoutMs = DEFAULT_TIMEOUT_MS, notifyOnUnauthorized = true } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const requestHeaders: Record<string, string> = { Accept: "application/json", ...headers };
  if (body !== undefined) requestHeaders["Content-Type"] = "application/json";
  if (authToken) requestHeaders.Authorization = `Bearer ${authToken}`;

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The server took too long to respond.", null);
    }
    throw new ApiError("Unable to reach the Nova Health server.", null);
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const errorBody = await readErrorBody(response);
    if (response.status === 401 && notifyOnUnauthorized) unauthorizedHandler?.();
    const message =
      typeof errorBody.detail === "string" ? errorBody.detail : `The server responded with status ${response.status}.`;
    throw new ApiError(message, response.status, errorBody.field_errors ?? {});
  }

  return (await response.json()) as T;
}

export function apiGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  return apiRequest<T>("GET", path, { timeoutMs });
}

export function apiPost<T>(path: string, body?: unknown, options: Omit<RequestOptions, "body"> = {}): Promise<T> {
  return apiRequest<T>("POST", path, { ...options, body });
}
