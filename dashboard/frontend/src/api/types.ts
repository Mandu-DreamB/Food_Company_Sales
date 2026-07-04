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
