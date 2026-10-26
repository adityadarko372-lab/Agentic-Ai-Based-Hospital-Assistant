/**
 * Minimal typed HTTP client for the Nova Health API.
 *
 * - All calls go to relative `/api/...` URLs (Vite proxies them to FastAPI).
 * - Every request has a timeout so the UI never hangs on a dead backend.
 * - Failures become an `ApiError` with a user-friendly message.
 */

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const DEFAULT_TIMEOUT_MS = 8000;

export async function apiGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ApiError(`The server responded with status ${response.status}.`, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The server took too long to respond.", null);
    }
    throw new ApiError("Unable to reach the Nova Health server.", null);
  } finally {
    clearTimeout(timer);
  }
}
