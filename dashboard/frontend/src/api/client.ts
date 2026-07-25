import type { IndicatorResult } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function listSources(): Promise<IndicatorResult[]> {
  const res = await fetch(`${BASE_URL}/api/sources`);
  if (!res.ok) throw new Error(`목록을 불러오지 못했습니다 (${res.status})`);
  return res.json();
}

export async function getSource(id: string): Promise<IndicatorResult> {
  const res = await fetch(`${BASE_URL}/api/sources/${id}`);
  if (!res.ok) throw new Error(`지표를 불러오지 못했습니다 (${res.status})`);
  return res.json();
}
