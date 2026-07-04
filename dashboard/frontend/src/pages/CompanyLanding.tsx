import { useState } from "react";
import { AFFILIATES, CATEGORIES } from "../data/affiliates";
import { AffiliateCard } from "../components/AffiliateCard";

const TABS = ["전체", ...CATEGORIES];

export function CompanyLanding() {
  const [activeTab, setActiveTab] = useState("전체");

  const visible = activeTab === "전체" ? AFFILIATES : AFFILIATES.filter((a) => a.category === activeTab);

  return (
    <div className="landing-page">
      <div className="landing-header">
        <div className="landing-eyebrow">SAMYANG GROUP</div>
        <h1>삼양그룹 계열사</h1>
      </div>

      <div className="landing-tabs">
        {TABS.map((tab) => (
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
