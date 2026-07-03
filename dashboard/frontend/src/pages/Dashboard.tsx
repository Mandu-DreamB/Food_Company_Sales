import { useSources } from "../context/SourcesContext";
import { IndicatorCard } from "../components/IndicatorCard";
import { CATEGORY_ORDER } from "../theme";

export function Dashboard() {
  const { sources, loading, error } = useSources();

  if (loading) return <div className="page-state">불러오는 중...</div>;
  if (error) return <div className="page-state error">{error}</div>;

  const byCategory = new Map<string, typeof sources>();
  for (const source of sources) {
    const list = byCategory.get(source.category) ?? [];
    list.push(source);
    byCategory.set(source.category, list);
  }

  const categories = [
    ...CATEGORY_ORDER.filter((c) => byCategory.has(c)),
    ...[...byCategory.keys()].filter((c) => !CATEGORY_ORDER.includes(c)),
  ];

  return (
    <div className="page">
      <h1>지표 대시보드</h1>
      <p className="page-subtitle">
        총 {sources.length}개 지표 · 카드를 클릭하면 상세 차트를 확인할 수 있습니다.
      </p>
      {categories.map((category) => (
        <section key={category} className="dashboard-section">
          <h2>{category}</h2>
          <div className="card-grid">
            {byCategory.get(category)!.map((source) => (
              <IndicatorCard key={source.id} source={source} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
