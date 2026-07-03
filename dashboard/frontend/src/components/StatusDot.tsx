import type { IndicatorResult } from "../api/types";

const STATUS_MAP: Record<IndicatorResult["status"], { color: string; label: string }> = {
  ok: { color: "var(--status-good)", label: "정상" },
  cached: { color: "var(--status-good)", label: "정상" },
  not_fetched: { color: "var(--text-muted)", label: "미조회" },
  missing_key: { color: "var(--status-warning)", label: "키 필요" },
  error: { color: "var(--status-critical)", label: "오류" },
};

export function StatusDot({ status, showLabel = false }: { status: IndicatorResult["status"]; showLabel?: boolean }) {
  const info = STATUS_MAP[status];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span
        aria-hidden
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: info.color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {showLabel && (
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{info.label}</span>
      )}
    </span>
  );
}
