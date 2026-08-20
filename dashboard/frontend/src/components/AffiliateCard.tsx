import { Link } from "react-router-dom";
import type { Affiliate } from "../api/types";

export function AffiliateCard({ affiliate }: { affiliate: Affiliate }) {
  return (
    <Link to={`/company/${affiliate.id}`} className="affiliate-card">
      <div className="affiliate-card-logo">{affiliate.logo_text}</div>
      <div className="affiliate-card-name">{affiliate.name}</div>
      <span className="affiliate-card-tag">{affiliate.category}</span>
    </Link>
  );
}
