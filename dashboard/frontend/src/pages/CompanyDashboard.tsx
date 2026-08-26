import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { askDbChat, getAffiliateBriefing, getTopIndicators, listAffiliates } from "../api/client";
import type { BriefingResult, ChartResult, IndicatorWithBriefing } from "../api/types";
import { ChartIcon, ChatWidget } from "../components/ChatWidget";
import { MultiSeriesChart } from "../components/MultiSeriesChart";
import { Spinner } from "../components/Spinner";

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

/** 챗봇이 만들어 준 차트 카드. 관련 지표 카드와 같은 컴포넌트로 그려서 화면이 따로 놀지 않게 한다. */
function ChatChartCard({ chart, onClose }: { chart: ChartResult; onClose: () => void }) {
  return (
    <div className="top-indicator-card chat-chart-card">
      <div className="top-indicator-header">
        <div className="top-indicator-title">{chart.title}</div>
        <div className="top-indicator-meta">
          챗봇이 만든 차트 · {chart.unit}
          {chart.transform === "yoy" && " · 전년동기대비"}
        </div>
        <button type="button" className="chat-chart-close" onClick={onClose} aria-label="차트 닫기">
          ×
        </button>
      </div>
      <MultiSeriesChart series={chart.series} />
    </div>
  );
}

function OverviewSourceInfo({ sources }: { sources: string[] }) {
  return (
    <span className="overview-info" tabIndex={0}>
      <span className="overview-info-icon" aria-hidden="true">
        i
      </span>
      <span className="overview-info-popover" role="tooltip">
        <span className="overview-info-title">분석 출처</span>
        {sources.length > 0 ? (
          <ul className="overview-info-list">
            {sources.map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
        ) : (
          <p className="overview-info-empty">
            공시 자료(사업보고서) 없이 업종 일반 정보로 작성했습니다. 이 계열사는 감사보고서만
            제출하고 있어 DART에 사업 설명이 공개돼 있지 않습니다.
          </p>
        )}
      </span>
    </span>
  );
}

function CompanyOverview({
  name,
  overview,
  sources,
}: {
  name: string;
  overview: string;
  sources: string[];
}) {
  return (
    <div className="overview-box">
      <div className="overview-head">
        <span className="overview-label">{name} 사업보고서</span>
        <span className="overview-sublabel">사업보고서(사업의 내용·주요 원재료)</span>
        <OverviewSourceInfo sources={sources} />
      </div>
      {overview.split("\n\n").map((paragraph, i) => (
        <p key={i} className={"overview-text" + (i === 0 ? " overview-text-lead" : "")}>
          {paragraph}
        </p>
      ))}
    </div>
  );
}

function TopIndicatorCard({ source }: { source: IndicatorWithBriefing }) {
  const briefing = source.briefing;
  const hasBriefing = briefing && briefing.status !== "not_generated" && briefing.text;

  return (
    <div className="top-indicator-card">
      <div className="top-indicator-header">
        <Link to={`/indicator/${source.id}`} className="top-indicator-title">
          {source.title}
        </Link>
        <div className="top-indicator-meta">
          {source.category} · {source.unit} · {source.frequency}
        </div>
      </div>

      {source.status === "missing_key" ? (
        <p className="empty-chart">{source.error}</p>
      ) : source.series.length === 0 ? (
        <p className="empty-chart">아직 수집된 데이터가 없습니다.</p>
      ) : (
        <MultiSeriesChart series={source.series} />
      )}

      {hasBriefing && (
        <div className="briefing-box">
          <div className="briefing-label">AI 요약</div>
          <p className="briefing-text">{briefing!.text}</p>
          {briefing!.generated_at && (
            <div className="briefing-time">
              {new Date(briefing!.generated_at).toLocaleString("ko-KR")} 기준
              {briefing!.status === "error" && " · 최신 갱신 실패, 이전 요약을 보여줍니다"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const DB_QUICK_REPLIES = [
  "WTI 유가 최근 값 알려줘",
  "FAO 세계 식품가격지수 최근 6개월 추이 보여줘",
  "지표 수집이 실패한 지표 있어?",
  "FAO 식품가격지수 곡물·유지류 최근 3년 그래프 보여줘",
];

export function CompanyDashboard() {
  const { affiliateId } = useParams<{ affiliateId: string }>();
  const [name, setName] = useState<string | null>(null);
  const [overview, setOverview] = useState<string | null>(null);
  const [overviewSources, setOverviewSources] = useState<string[]>([]);
  const [sources, setSources] = useState<IndicatorWithBriefing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatChart, setChatChart] = useState<ChartResult | null>(null);

  useEffect(() => {
    if (!affiliateId) return;
    setLoading(true);
    Promise.all([getTopIndicators(affiliateId), listAffiliates()])
      .then(([sourcesData, affiliateData]) => {
        setSources(sourcesData);
        const affiliate = affiliateData.affiliates.find((a) => a.id === affiliateId);
        setName(affiliate?.name ?? null);
        setOverview(affiliate?.overview ?? null);
        setOverviewSources(affiliate?.overview_sources ?? []);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    setChatChart(null);  // 계열사를 옮기면 이전 계열사 얘기로 만든 차트는 치운다
  }, [affiliateId]);

  if (loading) return <div className="page-state"><Spinner /></div>;
  if (error) return <div className="page-state error">{error}</div>;

  return (
    <div className="page">
      <h1>{name ?? "계열사"} 관련 지표</h1>
      <p className="page-subtitle">이 계열사와 가장 연관도가 높은 지표 {sources.length}개입니다.</p>
      {name && overview && <CompanyOverview name={name} overview={overview} sources={overviewSources} />}
      {sources.length === 0 && <div className="page-state">관련된 지표가 아직 없습니다.</div>}
      <div className="top-indicator-stack">
        {chatChart && <ChatChartCard chart={chatChart} onClose={() => setChatChart(null)} />}
        {sources.map((source) => (
          <TopIndicatorCard key={source.id} source={source} />
        ))}
      </div>
      {affiliateId && <Briefing affiliateId={affiliateId} />}
      <ChatWidget
        className="chat-widget-db"
        ask={askDbChat}
        title="지표 DB 챗봇"
        subtitle="수집된 지표 데이터를 직접 조회해 답해요"
        emptyHint="수집된 지표 데이터에 대해 물어보세요. 예시 질문을 눌러보세요."
        quickReplies={DB_QUICK_REPLIES}
        onChart={setChatChart}
        icon={<ChartIcon />}
      />
    </div>
  );
}
