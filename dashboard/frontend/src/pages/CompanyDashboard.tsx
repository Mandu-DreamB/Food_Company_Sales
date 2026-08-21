import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAffiliateBriefing, listAffiliates, listSources } from "../api/client";
import type { BriefingResult, IndicatorResult } from "../api/types";
import { IndicatorCard } from "../components/IndicatorCard";
import { Spinner } from "../components/Spinner";
import { groupByCategory } from "../theme";

function Briefing({ affiliateId }: { affiliateId: string }) {
  const [briefing, setBriefing] = useState<BriefingResult | null>(null);

  useEffect(() => {
    setBriefing(null);
    getAffiliateBriefing(affiliateId)
      .then(setBriefing)
      .catch(() => setBriefing(null));
  }, [affiliateId]);

  if (!briefing || briefing.status === "not_generated" || !briefing.text) return null;

  return (
    <div className="briefing-box">
      <div className="briefing-label">AI 브리핑</div>
      <p className="briefing-text">{briefing.text}</p>
      {briefing.generated_at && (
        <div className="briefing-time">
          {new Date(briefing.generated_at).toLocaleString("ko-KR")} 기준
          {briefing.status === "error" && " · 최신 갱신 실패, 이전 브리핑을 보여줍니다"}
        </div>
      )}
    </div>
  );
}

export function CompanyDashboard() {
  const { affiliateId } = useParams<{ affiliateId: string }>();
  const [name, setName] = useState<string | null>(null);
  const [sources, setSources] = useState<IndicatorResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!affiliateId) return;
    setLoading(true);
    Promise.all([listSources(affiliateId), listAffiliates()])
      .then(([sourcesData, affiliateData]) => {
        setSources(sourcesData);
        setName(affiliateData.affiliates.find((a) => a.id === affiliateId)?.name ?? null);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [affiliateId]);

  if (loading) return <div className="page-state"><Spinner /></div>;
  if (error) return <div className="page-state error">{error}</div>;

  return (
    <div className="page">
      <h1>{name ?? "계열사"} 관련 지표</h1>
      <p className="page-subtitle">
        이 계열사 업종과 관련도가 높은 {sources.length}개 지표입니다 ·{" "}
        <Link to="/dashboard">전체 지표 보기</Link>
      </p>
      {affiliateId && <Briefing affiliateId={affiliateId} />}
      {sources.length === 0 && <div className="page-state">관련된 지표가 아직 없습니다.</div>}
      {groupByCategory(sources).map(([category, items]) => (
        <section key={category} className="dashboard-section">
          <h2>{category}</h2>
          <div className="card-grid">
            {items.map((source) => (
              <IndicatorCard key={source.id} source={source} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
