import { Link } from "react-router-dom";
import type { IndicatorResult } from "../api/types";
import { StatusDot } from "./StatusDot";

export function IndicatorCard({ source }: { source: IndicatorResult }) {
  return (
    <Link to={`/indicator/${source.id}`} className="indicator-card">
      <div className="indicator-card-header">
        <StatusDot status={source.status} showLabel />
      </div>
      <div className="indicator-card-title">{source.title}</div>
      <div className="indicator-card-meta">
        {source.unit} · {source.frequency}
      </div>
    </Link>
  );
}
