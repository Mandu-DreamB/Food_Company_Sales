export type AffiliateCategory = "화학" | "식품" | "패키징" | "의약바이오" | "코스메틱" | "IT";

export interface Affiliate {
  id: string;
  name: string;
  category: AffiliateCategory;
  logoText: string;
}

export const CATEGORIES: AffiliateCategory[] = [
  "화학",
  "식품",
  "패키징",
  "의약바이오",
  "코스메틱",
  "IT",
];

export const AFFILIATES: Affiliate[] = [
  { id: "samyang-corp", name: "삼양사", category: "식품", logoText: "SAMYANG" },
  { id: "samyang-innochem", name: "삼양이노켐", category: "화학", logoText: "INNOCHEM" },
  { id: "samyang-packaging", name: "삼양패키징", category: "패키징", logoText: "PACKAGING" },
  { id: "samyang-biopharm", name: "삼양바이오팜", category: "의약바이오", logoText: "BIOPHARM" },
  { id: "samyang-cnt", name: "크레잇", category: "코스메틱", logoText: "KREYOL" },
  { id: "samyang-data", name: "삼양데이타시스템", category: "IT", logoText: "SAMYANG DS" },
];
