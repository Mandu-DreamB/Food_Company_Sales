import { useEffect, useState } from "react";
import { NavLink, useParams } from "react-router-dom";
import { useSources } from "../context/SourcesContext";
import { CATEGORY_ORDER } from "../theme";

export function Sidebar() {
  const { sources } = useSources();
  const { id: activeIndicatorId } = useParams<{ id: string }>();

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
      <NavLink to="/" className="sidebar-back">
        ← 계열사 목록
      </NavLink>
      <NavLink to="/dashboard" className="sidebar-home" end>
        지표 대시보드
      </NavLink>
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
