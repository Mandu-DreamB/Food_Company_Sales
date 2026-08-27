import type { AffiliateList, BriefingResult, DbChatAnswer, IndicatorResult, IndicatorWithBriefing } from "./types";

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

export async function getTopIndicators(affiliateId: string): Promise<IndicatorWithBriefing[]> {
  const res = await fetch(`${BASE_URL}/api/affiliates/${encodeURIComponent(affiliateId)}/top-indicators`);
  if (!res.ok) throw new Error(`관련 지표를 불러오지 못했습니다 (${res.status})`);
  return res.json();
}

/** 지표 DB를 직접 조회해 답하는 챗봇 (백엔드가 자연어를 읽기 전용 SQL로 바꿔 실행). */
export async function askDbChat(question: string): Promise<DbChatAnswer> {
  const res = await fetch(`${BASE_URL}/api/db-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    // 백엔드가 낸 502에는 detail이 있고, Render가 낸 Bad Gateway에는 없다. 이 둘을
    // 구분할 수 있어야 어디를 봐야 할지 정해진다.
    const detail = await res
      .json()
      .then((d: { detail?: string }) => d.detail)
      .catch(() => null);
    throw new Error(detail ?? `DB 챗봇 응답을 받지 못했습니다 (${res.status})`);
  }
  return res.json();
}
