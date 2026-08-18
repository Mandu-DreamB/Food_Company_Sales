import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Series } from "../api/types";
import { colorForIndex } from "../theme";

type ViewMode = "raw" | "indexed" | "grid" | "table";

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

const VIEW_LABELS: Record<ViewMode, string> = {
  raw: "원본 비교",
  indexed: "변화율 비교",
  grid: "개별 보기",
  table: "표로 보기",
};

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

function OverlayChart({ data, series }: { data: ChartRow[]; series: Series[] }) {
  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid stroke="var(--gridline)" strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="date"
          stroke="var(--baseline)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          stroke="var(--baseline)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={60}
        />
        <ChartTooltip />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 13 }} />}
        {series.map((s, i) => (
          <Line
            key={s.name}
            type="monotone"
            dataKey={s.name}
            stroke={colorForIndex(i)}
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function SeriesGrid({ series }: { series: Series[] }) {
  return (
    <div className="chart-grid">
      {series.map((s) => {
        const rows = s.points.map((p) => ({ date: p.date, value: p.value }));
        return (
          <div key={s.name} className="chart-grid-cell">
            <div className="chart-grid-title">{s.name}</div>
            <ResponsiveContainer width="100%" height={140}>
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

export function MultiSeriesChart({ series }: { series: Series[] }) {
  const manySeries = series.length > 8;
  const [mode, setMode] = useState<ViewMode>(manySeries ? "grid" : "raw");

  const data = useMemo(() => mergeSeries(series), [series]);
  const indexedSeriesData = useMemo(() => indexSeries(series), [series]);
  const indexedData = useMemo(() => mergeSeries(indexedSeriesData), [indexedSeriesData]);

  if (series.length === 0) {
    return <div className="empty-chart">표시할 데이터가 없습니다.</div>;
  }

  const showModeSwitch = series.length > 1;

  return (
    <div>
      {showModeSwitch && (
        <div className="chart-mode-switch">
          {(Object.keys(VIEW_LABELS) as ViewMode[]).map((m) => (
            <button
              key={m}
              type="button"
              className={`chart-mode-button${mode === m ? " active" : ""}`}
              onClick={() => setMode(m)}
            >
              {VIEW_LABELS[m]}
            </button>
          ))}
        </div>
      )}

      {mode === "raw" && <OverlayChart data={data} series={series} />}
      {mode === "indexed" && <OverlayChart data={indexedData} series={indexedSeriesData} />}
      {mode === "grid" && <SeriesGrid series={series} />}
      {mode === "table" && <SeriesTable data={data} series={series} />}
    </div>
  );
}
