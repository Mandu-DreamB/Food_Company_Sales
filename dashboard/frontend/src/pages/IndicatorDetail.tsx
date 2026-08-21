import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSource } from "../api/client";
import type { IndicatorResult } from "../api/types";
import { MultiSeriesChart } from "../components/MultiSeriesChart";
import { Spinner } from "../components/Spinner";
import { StatusBanner } from "../components/StatusBanner";
import { useSources } from "../context/SourcesContext";

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" />
    </svg>
  );
}

export function IndicatorDetail() {
  const { id } = useParams<{ id: string }>();
  const { reload: reloadSidebar } = useSources();
  const [source, setSource] = useState<IndicatorResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (isReload: boolean) => {
      if (!id) return;
      (isReload ? setRefreshing : setLoading)(true);
      getSource(id)
        .then((data) => {
          setSource(data);
          setError(null);
        })
        .catch((err) => setError(err.message))
        .finally(() => {
          setLoading(false);
          setRefreshing(false);
          reloadSidebar();
        });
    },
    [id, reloadSidebar],
  );

  useEffect(() => {
    load(false);
  }, [load]);

  if (loading) return <div className="page-state"><Spinner /></div>;
  if (error) return <div className="page-state error">{error}</div>;
  if (!source) return null;

  return (
    <div className="page">
      <div className="detail-header">
        <div>
          <h1>{source.title}</h1>
          <p className="page-subtitle">
            {source.category} · {source.unit} · {source.frequency}
          </p>
        </div>
        <button
          className={"refresh-button" + (refreshing ? " spinning" : "")}
          onClick={() => load(true)}
          disabled={refreshing}
          aria-label="다시 불러오기"
          title="다시 불러오기"
        >
          <RefreshIcon />
        </button>
      </div>

      <StatusBanner source={source} />

      {source.status !== "missing_key" && <MultiSeriesChart series={source.series} />}

      {source.fetched_at && (
        <p className="fetched-at">마지막 수집: {new Date(source.fetched_at).toLocaleString("ko-KR")}</p>
      )}
    </div>
  );
}
