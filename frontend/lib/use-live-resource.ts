"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type UseLiveResourceOptions<T> = {
  loader: () => Promise<T>;
  enabled?: boolean;
  refreshIntervalMs?: number;
  shouldRefresh?: (data: T | null) => boolean;
};

type UseLiveResourceResult<T> = {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  lastUpdated: string | null;
  refresh: () => Promise<void>;
  replaceData: (nextData: T) => void;
};

export function useLiveResource<T>({
  loader,
  enabled = true,
  refreshIntervalMs,
  shouldRefresh
}: UseLiveResourceOptions<T>): UseLiveResourceResult<T> {
  const mountedRef = useRef(false);
  const dataRef = useRef<T | null>(null);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(enabled);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const replaceData = useCallback((nextData: T) => {
    dataRef.current = nextData;
    setData(nextData);
    setLastUpdated(new Date().toISOString());
  }, []);

  const refresh = useCallback(async () => {
    if (!enabled) {
      return;
    }

    const hasPreviousData = dataRef.current !== null;
    if (hasPreviousData) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const nextData = await loader();
      if (!mountedRef.current) {
        return;
      }

      dataRef.current = nextData;
      setData(nextData);
      setError(null);
      setLastUpdated(new Date().toISOString());
    } catch (loadError) {
      if (!mountedRef.current) {
        return;
      }

      setError(loadError instanceof Error ? loadError.message : "Не удалось загрузить данные");
    } finally {
      if (!mountedRef.current) {
        return;
      }

      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [enabled, loader]);

  useEffect(() => {
    mountedRef.current = true;
    void refresh();

    return () => {
      mountedRef.current = false;
    };
  }, [refresh]);

  useEffect(() => {
    if (!enabled || !refreshIntervalMs) {
      return;
    }

    if (shouldRefresh && !shouldRefresh(data)) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refresh();
    }, refreshIntervalMs);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [data, enabled, refresh, refreshIntervalMs, shouldRefresh]);

  return {
    data,
    error,
    isLoading,
    isRefreshing,
    lastUpdated,
    refresh,
    replaceData
  };
}
