import type { AffiliateList, BriefingResult, IndicatorResult } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function listAffiliates(): Promise<AffiliateList> {
  const res = await fetch(`${BASE_URL}/api/affiliates`);
  if (!res.ok) throw new Error(`계열사 목록을 불러오지 못했습니다 (${res.status})`);
  return res.json();
}

export async function getAffiliateBriefing(affiliateId: string): Promise<BriefingResult> {
  const res = await fetch(`${BASE_URL}/api/affiliates/${encodeURIComponent(affiliateId)}/briefing`);
  if (!res.ok) throw new Error(`브리핑을 불러오지 못했습니다 (${res.status})`);
  return res.json();
}

export async function listSources(affiliateId?: string): Promise<IndicatorResult[]> {
  const qs = affiliateId ? `?affiliate_id=${encodeURIComponent(affiliateId)}` : "";
  const res = await fetch(`${BASE_URL}/api/sources${qs}`);
  if (!res.ok) throw new Error(`목록을 불러오지 못했습니다 (${res.status})`);
  return res.json();
}

export async function getSource(id: string): Promise<IndicatorResult> {
  const res = await fetch(`${BASE_URL}/api/sources/${id}`);
  if (!res.ok) throw new Error(`지표를 불러오지 못했습니다 (${res.status})`);
  return res.json();
}
