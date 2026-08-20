import { useSources } from "../context/SourcesContext";
import { IndicatorCard } from "../components/IndicatorCard";
import { groupByCategory } from "../theme";

export function Dashboard() {
  const { sources, loading, error } = useSources();

  if (loading) return <div className="page-state">불러오는 중...</div>;
  if (error) return <div className="page-state error">{error}</div>;

  return (
    <div className="page">
      <h1>지표 대시보드</h1>
      <p className="page-subtitle">
        총 {sources.length}개 지표 · 카드를 클릭하면 상세 차트를 확인할 수 있습니다.
      </p>
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
