import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSource } from "../api/client";
import type { IndicatorResult } from "../api/types";
import { MultiSeriesChart } from "../components/MultiSeriesChart";
import { StatusBanner } from "../components/StatusBanner";
import { useSources } from "../context/SourcesContext";

export function IndicatorDetail() {
  const { id } = useParams<{ id: string }>();
  const { reload: reloadSidebar } = useSources();
  const [source, setSource] = useState<IndicatorResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (refresh: boolean) => {
      if (!id) return;
      (refresh ? setRefreshing : setLoading)(true);
      getSource(id, refresh)
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

  if (loading) return <div className="page-state">불러오는 중...</div>;
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
        <button className="refresh-button" onClick={() => load(true)} disabled={refreshing}>
          {refreshing ? "새로고침 중..." : "새로고침"}
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
