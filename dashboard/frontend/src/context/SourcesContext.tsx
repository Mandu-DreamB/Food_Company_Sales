import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { listSources } from "../api/client";
import type { IndicatorResult } from "../api/types";

interface SourcesContextValue {
  sources: IndicatorResult[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const SourcesContext = createContext<SourcesContextValue | null>(null);

export function SourcesProvider({ children }: { children: ReactNode }) {
  const [sources, setSources] = useState<IndicatorResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    listSources()
      .then((data) => {
        setSources(data);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return (
    <SourcesContext.Provider value={{ sources, loading, error, reload }}>
      {children}
    </SourcesContext.Provider>
  );
}

export function useSources() {
  const ctx = useContext(SourcesContext);
  if (!ctx) throw new Error("useSources must be used within SourcesProvider");
  return ctx;
}
