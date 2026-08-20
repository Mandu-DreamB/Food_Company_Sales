export interface Affiliate {
  id: string;
  name: string;
  category: string;
  logo_text: string;
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
