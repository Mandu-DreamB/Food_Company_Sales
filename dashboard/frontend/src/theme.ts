// 이 순서는 장식이 아니라 색맹 안전성의 핵심 장치다 — 인접한 두 슬롯이 항상 구분 가능하도록
// 검증된 순서다 (validate_palette.js 통과). 색을 바꾸거나 순서를 섞으면 재검증이 필요하다.
export const CATEGORICAL_COLORS = [
  "#2a78d6", // 1 blue
  "#eb6834", // 2 orange
  "#1baf7a", // 3 aqua
  "#eda100", // 4 yellow
  "#e87ba4", // 5 magenta
  "#008300", // 6 green
  "#4a3aa7", // 7 violet
  "#e34948", // 8 red
];

export function colorForIndex(index: number): string {
  return CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length];
}

export const STATUS_COLORS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
};

export const CATEGORY_ORDER = [
  "에너지·원자재",
  "농축수산물",
  "금융시장",
  "금리·통화정책",
  "물가·고용",
  "소비·유통",
  "부동산",
  "자동차",
  "무역·수출",
  "계열사 주가",
];

export function groupByCategory<T extends { category: string }>(items: T[]): [string, T[]][] {
  const byCategory = new Map<string, T[]>();
  for (const item of items) {
    const list = byCategory.get(item.category) ?? [];
    list.push(item);
    byCategory.set(item.category, list);
  }

  const orderedKeys = [
    ...CATEGORY_ORDER.filter((c) => byCategory.has(c)),
    ...[...byCategory.keys()].filter((c) => !CATEGORY_ORDER.includes(c)),
  ];

  return orderedKeys.map((c) => [c, byCategory.get(c)!]);
}
