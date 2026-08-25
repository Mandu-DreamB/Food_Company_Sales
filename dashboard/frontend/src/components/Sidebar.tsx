import { useEffect, useState } from "react";
import { Link, NavLink, useParams } from "react-router-dom";
import { listAffiliates } from "../api/client";
import { useSources } from "../context/SourcesContext";
import { CATEGORY_ORDER } from "../theme";

const LAST_AFFILIATE_KEY = "sidebar:lastAffiliateId";

export function Sidebar() {
  const { sources } = useSources();
  const { id: activeIndicatorId, affiliateId: routeAffiliateId } = useParams<{
    id: string;
    affiliateId: string;
  }>();

  // 지표 상세(/indicator/:id)는 URL에 계열사 정보가 없어서, 계열사 페이지에서 넘어온 경우엔
  // 마지막으로 본 계열사를 기억해뒀다가 그대로 보여준다. 계열사 페이지 자체에 있을 땐 URL이 우선.
  const [affiliateId, setAffiliateId] = useState<string | null>(() => {
    if (routeAffiliateId) return routeAffiliateId;
    try {
      return localStorage.getItem(LAST_AFFILIATE_KEY);
    } catch {
      return null;
    }
  });
  const [affiliateName, setAffiliateName] = useState<string | null>(null);

  useEffect(() => {
    if (!routeAffiliateId) return;
    setAffiliateId(routeAffiliateId);
    try {
      localStorage.setItem(LAST_AFFILIATE_KEY, routeAffiliateId);
    } catch {
      // 프라이빗 모드 등 localStorage를 못 쓰는 환경이면 그냥 무시 (이번 세션에서만 표시 안 됨)
    }
  }, [routeAffiliateId]);

  useEffect(() => {
    if (!affiliateId) {
      setAffiliateName(null);
      return;
    }
    listAffiliates()
      .then((data) => setAffiliateName(data.affiliates.find((a) => a.id === affiliateId)?.name ?? null))
      .catch(() => setAffiliateName(null));
  }, [affiliateId]);

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

  const activeCategory = sources.find((s) => s.id === activeIndicatorId)?.category;

  const [openCategories, setOpenCategories] = useState<Set<string>>(
    () => new Set(activeCategory ? [activeCategory] : []),
  );

  // 지표 상세로 이동해서 활성 카테고리가 바뀌면, 그 카테고리는 항상 펼쳐진 상태로 맞춘다
  // (이미 열려 있던 다른 카테고리는 그대로 둔다).
  useEffect(() => {
    if (!activeCategory) return;
    setOpenCategories((prev) => (prev.has(activeCategory) ? prev : new Set(prev).add(activeCategory)));
  }, [activeCategory]);

  function toggleCategory(category: string) {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  }

  return (
    <nav className="sidebar">
      <Link to="/" className="sidebar-back">
        ← 계열사 목록
      </Link>
      <Link to={affiliateId ? `/company/${affiliateId}` : "/dashboard"} className="sidebar-brand">
        <span className="sidebar-brand-logo">SG</span>
        <span className="sidebar-brand-text">
          <span className="sidebar-brand-title">지표 대시보드</span>
          <span className="sidebar-brand-sub">{affiliateName ?? "전체 지표 보기"}</span>
        </span>
      </Link>
      {categories.map((category) => {
        const items = byCategory.get(category)!;
        const isOpen = openCategories.has(category);
        const hasActive = items.some((s) => s.id === activeIndicatorId);

        return (
          <div key={category} className={"sidebar-group" + (isOpen ? " open" : "")}>
            <button
              type="button"
              className={"sidebar-group-title" + (hasActive ? " has-active" : "")}
              onClick={() => toggleCategory(category)}
              aria-expanded={isOpen}
            >
              <span>{category}</span>
              <span className="sidebar-group-chevron" aria-hidden="true">
                ›
              </span>
            </button>
            {isOpen && (
              <div className="sidebar-group-items">
                {items.map((source) => (
                  <NavLink
                    key={source.id}
                    to={`/indicator/${source.id}`}
                    className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
                  >
                    <span className="sidebar-link-title">{source.title}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}
