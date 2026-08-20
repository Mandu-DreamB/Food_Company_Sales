import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import type { Series } from "../api/types";
import { colorForIndex } from "../theme";

type OverlayMode = "raw" | "indexed" | "table";
type RangeKey = "1y" | "5y" | "10y" | "all";

interface ChartRow {
  date: string;
  [seriesName: string]: string | number | null;
}

function mergeSeries(series: Series[]): ChartRow[] {
  const byDate = new Map<string, ChartRow>();

  for (const s of series) {
    for (const point of s.points) {
      const row = byDate.get(point.date) ?? { date: point.date };
      row[s.name] = point.value;
      byDate.set(point.date, row);
    }
  }

  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}

// 단위가 서로 다른 시리즈(예: 유가 $/BBL vs 천연가스 $/MMBtu)를 한 축에 같이 그리면 작은 쪽이
// 바닥에 눌려 안 보인다. 첫 유효값을 100으로 맞춰 "그 시점 대비 변화율"로 바꾸면 단위와 무관하게
// 추세를 비교할 수 있다. 두 축을 쓰는 대신 이 방식을 쓰는 이유는 dataviz 스킬의 원칙(단일 축) 때문.
function indexSeries(series: Series[]): Series[] {
  return series.map((s) => {
    const base = s.points.find((p) => p.value != null)?.value;
    if (!base) return s;
    return {
      name: s.name,
      points: s.points.map((p) => ({
        date: p.date,
        value: p.value == null ? null : (p.value / base) * 100,
      })),
    };
  });
}

const OVERLAY_LABELS: Record<OverlayMode, string> = {
  raw: "원본 비교",
  indexed: "변화율 비교",
  table: "표로 보기",
};

const RANGE_LABELS: Record<RangeKey, string> = { "1y": "1Y", "5y": "5Y", "10y": "10Y", all: "전체" };
const RANGE_YEARS: Record<"1y" | "5y" | "10y", number> = { "1y": 1, "5y": 5, "10y": 10 };

// 지표마다 마지막 수집 시점이 달라서(오늘일 수도, 몇 달 전일 수도) "오늘 - N년"이 아니라
// "이 지표의 가장 최근 데이터 시점 - N년"을 기준으로 잘라야 실제로 최근 N년치가 남는다.
function filterByRange(series: Series[], range: RangeKey): Series[] {
  if (range === "all") return series;

  let latest: string | null = null;
  for (const s of series) {
    for (const p of s.points) {
      if (latest === null || p.date > latest) latest = p.date;
    }
  }
  if (latest === null) return series;

  const cutoff = new Date(latest);
  cutoff.setFullYear(cutoff.getFullYear() - RANGE_YEARS[range]);
  const cutoffIso = cutoff.toISOString().slice(0, 10);

  return series.map((s) => ({
    name: s.name,
    points: s.points.filter((p) => p.date >= cutoffIso),
  }));
}

function ChartTooltip() {
  return (
    <Tooltip
      contentStyle={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        fontSize: 13,
      }}
      labelStyle={{ color: "var(--text-secondary)" }}
      cursor={{ stroke: "var(--baseline)", strokeDasharray: "3 3" }}
    />
  );
}

// 값 옆에 시리즈 색 점을 찍어주는 커스텀 툴팁 (원본/변화율 비교 차트 전용).
function AreaTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      {payload.map((entry) => (
        <div key={entry.dataKey as string} className="chart-tooltip-row">
          <span className="chart-tooltip-dot" style={{ background: entry.color }} />
          <span className="chart-tooltip-name">{String(entry.dataKey)}</span>
          <span className="chart-tooltip-value">
            {typeof entry.value === "number"
              ? entry.value.toLocaleString("ko-KR", { maximumFractionDigits: 2 })
              : "–"}
          </span>
        </div>
      ))}
    </div>
  );
}

function OverlayChart({ data, series }: { data: ChartRow[]; series: Series[] }) {
  return (
    <ResponsiveContainer width="100%" height={380}>
      <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <defs>
          {series.map((s, i) => (
            <linearGradient key={s.name} id={`chart-fill-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colorForIndex(i)} stopOpacity={0.32} />
              <stop offset="95%" stopColor={colorForIndex(i)} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="var(--gridline)" strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="date"
          stroke="var(--baseline)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          minTickGap={40}
        />
        <YAxis
          stroke="var(--baseline)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={60}
        />
        <Tooltip content={AreaTooltip} cursor={{ stroke: "var(--baseline)", strokeDasharray: "3 3" }} />
        {series.length > 1 && <Legend iconType="square" wrapperStyle={{ fontSize: 13 }} />}
        {series.map((s, i) => (
          <Area
            key={s.name}
            type="monotone"
            dataKey={s.name}
            stroke={colorForIndex(i)}
            strokeWidth={2}
            fill={`url(#chart-fill-${i})`}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

function latestPoint(points: { date: string; value: number | null }[]) {
  for (let i = points.length - 1; i >= 0; i--) {
    if (points[i].value != null) return points[i];
  }
  return null;
}

function SeriesGrid({ series }: { series: Series[] }) {
  return (
    <div className="chart-grid">
      {series.map((s) => {
        const rows = s.points.map((p) => ({ date: p.date, value: p.value }));
        const latest = latestPoint(rows);
        return (
          <div key={s.name} className="chart-grid-cell">
            <div className="chart-grid-title">{s.name}</div>
            {latest ? (
              <div className="chart-grid-latest">
                {latest.value!.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}
                <span className="chart-grid-latest-date">{latest.date}</span>
              </div>
            ) : (
              <div className="chart-grid-latest chart-grid-latest-empty">데이터 없음</div>
            )}
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={rows} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                <XAxis dataKey="date" hide />
                <YAxis
                  stroke="var(--baseline)"
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  width={44}
                  domain={["auto", "auto"]}
                />
                <ChartTooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#2a78d6"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}

function SeriesTable({ data, series }: { data: ChartRow[]; series: Series[] }) {
  return (
    <div className="chart-table-wrap">
      <table className="chart-table">
        <thead>
          <tr>
            <th>날짜</th>
            {series.map((s) => (
              <th key={s.name}>{s.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.date}>
              <td>{row.date}</td>
              {series.map((s) => {
                const v = row[s.name];
                return <td key={s.name}>{typeof v === "number" ? v.toLocaleString("ko-KR") : "–"}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RangeSwitch({ range, onChange }: { range: RangeKey; onChange: (r: RangeKey) => void }) {
  return (
    <div className="chart-mode-switch">
      {(Object.keys(RANGE_LABELS) as RangeKey[]).map((r) => (
        <button
          key={r}
          type="button"
          className={`chart-mode-button${range === r ? " active" : ""}`}
          onClick={() => onChange(r)}
        >
          {RANGE_LABELS[r]}
        </button>
      ))}
    </div>
  );
}

export function MultiSeriesChart({ series }: { series: Series[] }) {
  const [overlayMode, setOverlayMode] = useState<OverlayMode>("raw");
  const [range, setRange] = useState<RangeKey>("all");

  const ranged = useMemo(() => filterByRange(series, range), [series, range]);
  const data = useMemo(() => mergeSeries(ranged), [ranged]);
  const indexedSeriesData = useMemo(() => indexSeries(ranged), [ranged]);
  const indexedData = useMemo(() => mergeSeries(indexedSeriesData), [indexedSeriesData]);

  if (series.length === 0) {
    return <div className="empty-chart">표시할 데이터가 없습니다.</div>;
  }

  const noData = ranged.every((s) => s.points.length === 0);
  const hasMultipleSeries = series.length > 1;

  return (
    <div className="chart-stack">
      <div className="chart-top-bar">
        <RangeSwitch range={range} onChange={setRange} />
      </div>

      {hasMultipleSeries && (
        <section className="chart-section">
          <h3 className="chart-section-title">주요 지표</h3>
          {noData ? (
            <div className="empty-chart">선택한 기간에 데이터가 없습니다.</div>
          ) : (
            <SeriesGrid series={ranged} />
          )}
        </section>
      )}

      <section className="chart-card">
        <div className="chart-card-header">
          <h3 className="chart-section-title">가격 추이</h3>
          {hasMultipleSeries && (
            <div className="chart-mode-switch">
              {(Object.keys(OVERLAY_LABELS) as OverlayMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`chart-mode-button${overlayMode === m ? " active" : ""}`}
                  onClick={() => setOverlayMode(m)}
                >
                  {OVERLAY_LABELS[m]}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="chart-card-body">
          {noData ? (
            <div className="empty-chart">선택한 기간에 데이터가 없습니다.</div>
          ) : (
            <>
              {(overlayMode === "raw" || !hasMultipleSeries) && <OverlayChart data={data} series={ranged} />}
              {overlayMode === "indexed" && hasMultipleSeries && (
                <OverlayChart data={indexedData} series={indexedSeriesData} />
              )}
              {overlayMode === "table" && hasMultipleSeries && <SeriesTable data={data} series={ranged} />}
            </>
          )}
        </div>
      </section>
    </div>
  );
}
