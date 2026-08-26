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

// 접근 토큰은 빌드에 넣지 않는다. VITE_ 변수는 번들에 그대로 박혀서 페이지를 연 사람이면
// 누구나 devtools에서 읽을 수 있고, 그러면 "URL을 아는 사람"을 막겠다는 목적이 사라진다.
// 대신 처음 401을 받았을 때 한 번 입력받아 이 브라우저에만 저장한다.
const TOKEN_KEY = "dbChat:token";

const readToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return ""; // 프라이빗 모드 등 localStorage를 못 쓰면 매번 물어본다
  }
};

function askForToken(): string | null {
  const entered = window.prompt("DB 챗봇 접근 토큰을 입력하세요.");
  if (!entered) return null;
  try {
    localStorage.setItem(TOKEN_KEY, entered);
  } catch {
    // 저장 못 해도 이번 요청에는 쓸 수 있다
  }
  return entered;
}

/** 지표 DB를 직접 조회해 답하는 챗봇 (백엔드가 자연어를 읽기 전용 SQL로 바꿔 실행). */
export async function askDbChat(question: string): Promise<DbChatAnswer> {
  const send = (token: string) =>
    fetch(`${BASE_URL}/api/db-chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { "X-App-Token": token } : {}) },
      body: JSON.stringify({ question }),
    });

  let res = await send(readToken());
  if (res.status === 401) {
    const entered = askForToken();
    if (entered === null) throw new Error("접근 토큰이 필요합니다.");
    res = await send(entered);
    if (res.status === 401) {
      try {
        localStorage.removeItem(TOKEN_KEY); // 틀린 토큰을 남겨두면 다음에도 계속 막힌다
      } catch {
        // 지우지 못해도 다음 요청에서 다시 물어본다
      }
      throw new Error("접근 토큰이 올바르지 않습니다.");
    }
  }
  if (!res.ok) throw new Error(`DB 챗봇 응답을 받지 못했습니다 (${res.status})`);
  return res.json();
}
