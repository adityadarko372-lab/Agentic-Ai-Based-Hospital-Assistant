import { useCallback, useEffect, useRef, useState } from "react";

interface ApiResource<T> {
  data: T | null;
  error: string | null;
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
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const result = await loader();
      if (!mounted.current) return;
      setData(result);
      setError(null);
    } catch (caught) {
      if (!mounted.current) return;
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
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

  return { data, error, loading, reload };
}
