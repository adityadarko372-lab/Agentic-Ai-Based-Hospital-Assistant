import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../services/apiClient";

interface ApiResource<T> {
  data: T | null;
  error: string | null;
  /** HTTP status of the last failure (null for network errors or success). */
  errorStatus: number | null;
  loading: boolean;
  reload: () => Promise<void>;
}

/**
 * Loads data from the API and tracks loading / error state.
 * `loader` should be a stable function (for example from novaApi).
 */
export function useApiResource<T>(loader: () => Promise<T>): ApiResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const result = await loader();
      if (!mounted.current) return;
      setData(result);
      setError(null);
      setErrorStatus(null);
    } catch (caught) {
      if (!mounted.current) return;
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
      setErrorStatus(caught instanceof ApiError ? caught.status : null);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [loader]);

  useEffect(() => {
    mounted.current = true;
    void reload();
    return () => {
      mounted.current = false;
    };
  }, [reload]);

  return { data, error, errorStatus, loading, reload };
}
