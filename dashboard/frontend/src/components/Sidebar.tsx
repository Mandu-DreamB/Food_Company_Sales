import { NavLink } from "react-router-dom";
import { useSources } from "../context/SourcesContext";
import { CATEGORY_ORDER } from "../theme";
import { StatusDot } from "./StatusDot";

export function Sidebar() {
  const { sources } = useSources();

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
    <nav className="sidebar">
      <NavLink to="/" className="sidebar-home" end>
        지표 대시보드
      </NavLink>
      {categories.map((category) => (
        <div key={category} className="sidebar-group">
          <div className="sidebar-group-title">{category}</div>
          {byCategory.get(category)!.map((source) => (
            <NavLink
              key={source.id}
              to={`/indicator/${source.id}`}
              className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
            >
              <StatusDot status={source.status} />
              <span className="sidebar-link-title">{source.title}</span>
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}
