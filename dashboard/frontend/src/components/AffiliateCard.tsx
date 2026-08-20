import { useState } from "react";
import { Link } from "react-router-dom";
import type { Affiliate } from "../api/types";

// 계열사 id -> public/logo/ 안의 파일명. 삼양사(화학/식품/코스메틱)는 사업부만 다를 뿐
// 같은 법인이라 로고 파일 하나(samyang-corp)를 공유한다. 각 회사 공식 사이트에서 내려받음.
const LOGO_FILES: Record<string, string> = {
  "samyang-holdings": "samyang-holdings.svg",
  "samyang-chemical": "samyang-corp.svg",
  "samyang-food": "samyang-corp.svg",
  "samyang-cosmetic": "samyang-corp.svg",
  "samnam-petrochemical": "samnam-petrochemical.svg",
  "samyang-chemical-corp": "samyang-chemical-corp.svg",
  "samyang-innochem": "samyang-innochem.svg",
  "samyang-finetechnology": "samyang-finetechnology.svg",
  "samyang-kci": "samyang-kci.svg",
  "samyang-ncchem": "samyang-ncchem.svg",
  verdant: "verdant.webp",
  "samyang-biopharm": "samyang-biopharm.svg",
  "samyang-packaging": "samyang-packaging.svg",
  "samyang-data-system": "samyang-data-system.svg",
};

export function AffiliateCard({ affiliate }: { affiliate: Affiliate }) {
  const [imgFailed, setImgFailed] = useState(false);
  const logoFile = LOGO_FILES[affiliate.id];

  return (
    <Link to={`/company/${affiliate.id}`} className="affiliate-card">
      <div className="affiliate-card-logo">
        {logoFile && !imgFailed ? (
          <img
            src={`/logo/${logoFile}`}
            alt={`${affiliate.name} 로고`}
            className="affiliate-card-logo-img"
            onError={() => setImgFailed(true)}
          />
        ) : (
          affiliate.logo_text
        )}
      </div>
      <div className="affiliate-card-name">{affiliate.name}</div>
      <span className="affiliate-card-tag">{affiliate.category}</span>
    </Link>
  );
}
