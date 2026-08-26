export interface Affiliate {
  id: string;
  name: string;
  category: string;
  logo_text: string;
  overview: string | null;
  overview_sources: string[];
}

export interface AffiliateList {
  categories: string[];
  affiliates: Affiliate[];
}

export interface BriefingResult {
  status: "ok" | "error" | "not_generated";
  text: string | null;
  generated_at: string | null;
}

export interface Point {
  date: string;
  value: number | null;
}

export interface Series {
  name: string;
  points: Point[];
}

export interface IndicatorResult {
  id: string;
  title: string;
  category: string;
  unit: string;
  frequency: string;
  missing_env: string[];
  status: "ok" | "missing_key" | "not_fetched" | "cached" | "error";
  error: string | null;
  fetched_at: string | null;
  series: Series[];
}

export interface IndicatorWithBriefing extends IndicatorResult {
  briefing: BriefingResult | null;
}

/** DB 챗봇이 만든 차트. 스펙은 LLM이 정하지만 값은 서버가 DB에서 읽어 채운다. */
export interface ChartResult {
  title: string;
  unit: string;
  transform: "none" | "yoy";
  series: Series[];
}

export interface DbChatAnswer {
  answer: string;
  sql: string | null;
  chart: ChartResult | null;
}
