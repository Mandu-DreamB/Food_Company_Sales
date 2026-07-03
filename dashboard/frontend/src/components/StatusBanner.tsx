import type { IndicatorResult } from "../api/types";

export function StatusBanner({ source }: { source: IndicatorResult }) {
  if (source.status === "missing_key") {
    return (
      <div className="banner banner-warning">
        이 지표는 <code>{source.missing_env.join(", ")}</code> 환경변수가 필요합니다.
        <code>dashboard/backend/.env</code>에 키를 채운 뒤 백엔드를 재시작하세요.
      </div>
    );
  }

  if (source.status === "error") {
    return (
      <div className="banner banner-critical">
        데이터 수집에 실패했습니다: {source.error}
        {source.series.length > 0 && " (이전에 수집된 데이터를 표시합니다.)"}
      </div>
    );
  }

  return null;
}
