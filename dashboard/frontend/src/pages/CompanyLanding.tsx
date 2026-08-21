import { useEffect, useState } from "react";
import { listAffiliates } from "../api/client";
import type { AffiliateList } from "../api/types";
import { AffiliateCard } from "../components/AffiliateCard";
import { Spinner } from "../components/Spinner";

export function CompanyLanding() {
  const [data, setData] = useState<AffiliateList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("전체");

  useEffect(() => {
    listAffiliates()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="page-state error">{error}</div>;
  if (!data) return <div className="page-state"><Spinner /></div>;

  const tabs = ["전체", ...data.categories];
  const visible =
    activeTab === "전체"
      ? data.affiliates
      : data.affiliates.filter((a) => a.category === activeTab);

  return (
    <div className="landing-page">
      <div className="landing-header">
        <div className="landing-eyebrow">SAMYANG GROUP</div>
        <h1>삼양그룹 계열사</h1>
      </div>

      <div className="landing-tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={"landing-tab" + (tab === activeTab ? " active" : "")}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="affiliate-grid">
        {visible.map((affiliate) => (
          <AffiliateCard key={affiliate.id} affiliate={affiliate} />
        ))}
      </div>
    </div>
  );
}
