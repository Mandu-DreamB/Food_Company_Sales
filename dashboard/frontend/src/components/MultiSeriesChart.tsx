import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import {
  CartesianGrid,
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

type ViewMode = "chart" | "table";
type RangeKey = "1m" | "3m" | "6m" | "1y" | "all";

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

const RANGE_LABELS: Record<RangeKey, string> = { "1m": "1M", "3m": "3M", "6m": "6M", "1y": "1Y", all: "전체" };
const RANGE_MONTHS: Record<Exclude<RangeKey, "all">, number> = { "1m": 1, "3m": 3, "6m": 6, "1y": 12 };

// 지표마다 마지막 수집 시점이 달라서(오늘일 수도, 몇 달 전일 수도) "오늘 - N개월"이 아니라
// "이 지표의 가장 최근 데이터 시점 - N개월"을 기준으로 잘라야 실제로 최근 구간이 남는다.
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
  cutoff.setMonth(cutoff.getMonth() - RANGE_MONTHS[range]);
  const cutoffIso = cutoff.toISOString().slice(0, 10);

  return series.map((s) => ({
    name: s.name,
    points: s.points.filter((p) => p.date >= cutoffIso),
  }));
}

// 차트 영역 위에서 휠로 확대/축소, 드래그로 좌우 이동할 수 있게 하는 훅. recharts 자체엔 이
// 기능이 없어서, 보여줄 구간을 [start, end] 인덱스로 직접 들고 있다가 그 구간만 잘라 넘긴다.
const MIN_WINDOW = 10;

function useZoomPan(length: number) {
  const [win, setWin] = useState<[number, number]>([0, Math.max(0, length - 1)]);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dragStart = useRef<{ x: number; win: [number, number] } | null>(null);
  const winRef = useRef(win);
  winRef.current = win;

  useEffect(() => {
    setWin([0, Math.max(0, length - 1)]);
  }, [length]);

  const clamp = useCallback(
    (start: number, end: number): [number, number] => {
      let s = start;
      let e = end;
      if (s < 0) {
        e -= s;
        s = 0;
      }
      if (e > length - 1) {
        s -= e - (length - 1);
        e = length - 1;
      }
      return [Math.max(0, s), Math.min(length - 1, e)];
    },
    [length],
  );

  // 리액트가 onWheel/onTouchMove를 브라우저 기본값처럼 passive 리스너로 붙여버려서,
  // 그 안에서 부르는 e.preventDefault()가 조용히 무시되고 페이지가 그대로 스크롤된다
  // (트랙패드 두 손가락 드래그가 특히 이 경로를 탄다). { passive: false }로 DOM에
  // 직접 리스너를 달아야 실제로 막힌다.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // 다크 툴팁은 이 컨테이너 안쪽에 떠 있어서, 툴팁 목록을 스크롤/클릭하려는 시도까지
    // 차트 확대·이동 로직이 가로채 버린다. 이벤트 타깃이 툴팁 내부면 그냥 흘려보낸다.
    function isInsideTooltip(target: EventTarget | null) {
      return target instanceof HTMLElement && target.closest(".chart-tooltip-dark") != null;
    }

    function handleWheel(e: WheelEvent) {
      if (isInsideTooltip(e.target)) return;
      if (length <= MIN_WINDOW) {
        e.preventDefault();
        return;
      }
      e.preventDefault();
      const zoomIn = e.deltaY < 0;
      setWin(([s, en]) => {
        const size = en - s;
        const factor = zoomIn ? 0.85 : 1.18;
        const newSize = Math.max(MIN_WINDOW, Math.min(length - 1, Math.round(size * factor)));
        const center = (s + en) / 2;
        const newStart = Math.round(center - newSize / 2);
        return clamp(newStart, newStart + newSize);
      });
    }

    function panBy(clientX: number, startX: number, startWin: [number, number]) {
      const width = el!.clientWidth || 1;
      const [s0, e0] = startWin;
      const pxPerIndex = width / Math.max(1, e0 - s0);
      // 오른쪽으로 끌면(dx>0) 더 과거 구간이 드러나야 자연스러운 "타임라인 드래그" 동작이 된다.
      const dIndex = Math.round(-(clientX - startX) / pxPerIndex);
      setWin(clamp(s0 + dIndex, e0 + dIndex));
    }

    function handleTouchStart(e: TouchEvent) {
      if (e.touches.length !== 1 || isInsideTooltip(e.target)) return;
      dragStart.current = { x: e.touches[0].clientX, win: winRef.current };
      setDragging(true);
    }

    function handleTouchMove(e: TouchEvent) {
      if (!dragStart.current || e.touches.length !== 1) return;
      e.preventDefault();
      panBy(e.touches[0].clientX, dragStart.current.x, dragStart.current.win);
    }

    function handleTouchEnd() {
      dragStart.current = null;
      setDragging(false);
    }

    el.addEventListener("wheel", handleWheel, { passive: false });
    el.addEventListener("touchstart", handleTouchStart, { passive: true });
    el.addEventListener("touchmove", handleTouchMove, { passive: false });
    el.addEventListener("touchend", handleTouchEnd);
    return () => {
      el.removeEventListener("wheel", handleWheel);
      el.removeEventListener("touchstart", handleTouchStart);
      el.removeEventListener("touchmove", handleTouchMove);
      el.removeEventListener("touchend", handleTouchEnd);
    };
  }, [length, clamp]);

  function onMouseDown(e: ReactMouseEvent<HTMLDivElement>) {
    // 툴팁 목록 위에서 누른 거면 스크롤바 조작이니 그냥 흘려보낸다.
    if ((e.target as HTMLElement).closest(".chart-tooltip-dark")) return;
    // 기본 동작(텍스트 드래그 선택)을 막아야 브라우저가 선택 영역을 따라가려고
    // 페이지를 위아래로 자동 스크롤하는 걸 막을 수 있다.
    e.preventDefault();
    dragStart.current = { x: e.clientX, win };
    setDragging(true);
  }

  function onMouseMove(e: ReactMouseEvent<HTMLDivElement>) {
    if (!dragStart.current || !containerRef.current) return;
    e.preventDefault();
    const width = containerRef.current.clientWidth || 1;
    const [s0, e0] = dragStart.current.win;
    const pxPerIndex = width / Math.max(1, e0 - s0);
    const dIndex = Math.round(-(e.clientX - dragStart.current.x) / pxPerIndex);
    setWin(clamp(s0 + dIndex, e0 + dIndex));
  }

  function endDrag() {
    dragStart.current = null;
    setDragging(false);
  }

  return { win, containerRef, dragging, onMouseDown, onMouseMove, onMouseUp: endDrag, onMouseLeave: endDrag };
}

function pctChange(current: number | null, previous: number | null): number | null {
  if (typeof current !== "number" || typeof previous !== "number" || previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

// 값 옆에 시리즈 색 점 + 전일 대비 변화율을 보여주는 다크 툴팁.
// 드래그로 구간을 옮기는 동안엔 마우스가 지나는 지점마다 내용이 계속 바뀌어서 오히려
// 방해가 되므로, 그 동안은(suppressed) 아예 띄우지 않는다.
function PriceTooltip({
  active,
  payload,
  label,
  data,
  suppressed,
}: TooltipContentProps & { data: ChartRow[]; suppressed: boolean }) {
  if (suppressed || !active || !payload || payload.length === 0) return null;

  const idx = data.findIndex((row) => row.date === label);
  const prevRow = idx > 0 ? data[idx - 1] : null;

  return (
    <div className="chart-tooltip chart-tooltip-dark">
      <div className="chart-tooltip-label chart-tooltip-label-dark">{label}</div>
      {payload.map((entry) => {
        const key = entry.dataKey as string;
        const value = typeof entry.value === "number" ? entry.value : null;
        const prevValue = prevRow ? (prevRow[key] as number | null) : null;
        const pct = pctChange(value, prevValue);
        return (
          <div key={key} className="chart-tooltip-row">
            <span className="chart-tooltip-dot" style={{ background: entry.color }} />
            <span className="chart-tooltip-name">{key}</span>
            <span className="chart-tooltip-value">
              {value != null ? value.toLocaleString("ko-KR", { maximumFractionDigits: 2 }) : "–"}
            </span>
            {pct != null && (
              <span className={"chart-tooltip-pct " + (pct >= 0 ? "pos" : "neg")}>
                {pct >= 0 ? "+" : ""}
                {pct.toFixed(1)}%
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function LegendRow({
  series,
  hidden,
  onToggle,
  onToggleAll,
}: {
  series: Series[];
  hidden: Set<string>;
  onToggle: (name: string) => void;
  onToggleAll: () => void;
}) {
  const allVisible = hidden.size === 0;

  return (
    <div className="chart-legend-row">
      <label className="chart-legend-item chart-legend-all">
        <input type="checkbox" checked={allVisible} onChange={onToggleAll} />
        전체
      </label>
      {series.map((s, i) => (
        <label key={s.name} className="chart-legend-item">
          <input type="checkbox" checked={!hidden.has(s.name)} onChange={() => onToggle(s.name)} />
          <span className="chart-legend-swatch" style={{ background: colorForIndex(i) }} />
          {s.name}
        </label>
      ))}
    </div>
  );
}

function PriceChart({
  data,
  series,
  indexed,
}: {
  data: ChartRow[];
  series: Series[];
  indexed: boolean;
}) {
  const zoom = useZoomPan(data.length);
  const [winStart, winEnd] = zoom.win;
  const visibleData = useMemo(() => data.slice(winStart, winEnd + 1), [data, winStart, winEnd]);

  const startDate = visibleData[0]?.date;
  const endDate = visibleData[visibleData.length - 1]?.date;

  return (
    <div>
      <div
        ref={zoom.containerRef}
        className={"chart-zoomable" + (zoom.dragging ? " dragging" : "")}
        onMouseDown={zoom.onMouseDown}
        onMouseMove={zoom.onMouseMove}
        onMouseUp={zoom.onMouseUp}
        onMouseLeave={zoom.onMouseLeave}
      >
        <ResponsiveContainer width="100%" height={480}>
          <LineChart data={visibleData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
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
              domain={["auto", "auto"]}
              label={
                indexed
                  ? { value: "100 = 시작", angle: -90, position: "insideLeft", fill: "var(--text-muted)", fontSize: 11 }
                  : undefined
              }
            />
            <Tooltip
              content={(props) => <PriceTooltip {...props} data={visibleData} suppressed={zoom.dragging} />}
              cursor={zoom.dragging ? false : { stroke: "var(--baseline)", strokeDasharray: "3 3" }}
            />
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
      </div>
      {startDate && endDate && (
        <div className="chart-zoom-caption">
          스크롤 줌인/아웃 · 드래그 좌우 이동 · {startDate}~{endDate}
        </div>
      )}
    </div>
  );
}

function latestPoint(points: { date: string; value: number | null }[]) {
  for (let i = points.length - 1; i >= 0; i--) {
    if (points[i].value != null) return points[i];
  }
  return null;
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
          {r === "all" ? "↺ 전체" : RANGE_LABELS[r]}
        </button>
      ))}
    </div>
  );
}

export function MultiSeriesChart({ series }: { series: Series[] }) {
  const [range, setRange] = useState<RangeKey>("1y");
  const [viewMode, setViewMode] = useState<ViewMode>("chart");
  const [indexed, setIndexed] = useState(true);
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const ranged = useMemo(() => filterByRange(series, range), [series, range]);
  const rawData = useMemo(() => mergeSeries(ranged), [ranged]);
  const indexedSeriesData = useMemo(() => indexSeries(ranged), [ranged]);
  const indexedData = useMemo(() => mergeSeries(indexedSeriesData), [indexedSeriesData]);

  if (series.length === 0) {
    return <div className="empty-chart">표시할 데이터가 없습니다.</div>;
  }

  const noData = ranged.every((s) => s.points.length === 0);
  const hasMultipleSeries = series.length > 1;

  const useIndexed = indexed && hasMultipleSeries;
  const activeData = useIndexed ? indexedData : rawData;
  const activeSeries = useIndexed ? indexedSeriesData : ranged;
  const visibleSeries = activeSeries.filter((s) => !hidden.has(s.name));

  function toggleSeries(name: string) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function toggleAll() {
    setHidden((prev) => (prev.size > 0 ? new Set() : new Set(ranged.map((s) => s.name))));
  }

  return (
    <div className="chart-stack">
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
          <div className="chart-controls">
            <RangeSwitch range={range} onChange={setRange} />
            <div className="chart-mode-switch">
              <button
                type="button"
                className={`chart-mode-button${viewMode === "chart" ? " active" : ""}`}
                onClick={() => setViewMode("chart")}
              >
                차트
              </button>
              <button
                type="button"
                className={`chart-mode-button${viewMode === "table" ? " active" : ""}`}
                onClick={() => setViewMode("table")}
              >
                표
              </button>
            </div>
            {hasMultipleSeries && (
              <label className="chart-index-toggle">
                <input type="checkbox" checked={indexed} onChange={(e) => setIndexed(e.target.checked)} />
                지수화
              </label>
            )}
          </div>
          {hasMultipleSeries && (
            <LegendRow series={ranged} hidden={hidden} onToggle={toggleSeries} onToggleAll={toggleAll} />
          )}
        </div>

        <div className="chart-card-body">
          {noData ? (
            <div className="empty-chart">선택한 기간에 데이터가 없습니다.</div>
          ) : viewMode === "chart" ? (
            <PriceChart data={activeData} series={visibleSeries} indexed={useIndexed} />
          ) : (
            <SeriesTable data={activeData} series={visibleSeries} />
          )}
        </div>
      </section>
    </div>
  );
}
