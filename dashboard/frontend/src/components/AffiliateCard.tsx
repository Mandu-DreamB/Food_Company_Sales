import { Link } from "react-router-dom";
import type { Affiliate } from "../data/affiliates";

export function AffiliateCard({ affiliate }: { affiliate: Affiliate }) {
  return (
    <Link to="/dashboard" className="affiliate-card">
      <div className="affiliate-card-logo">{affiliate.logoText}</div>
      <div className="affiliate-card-name">{affiliate.name}</div>
      <span className="affiliate-card-tag">{affiliate.category}</span>
    </Link>
  );
}
