import { useQuery } from "@tanstack/react-query";
import { getKpiForecast } from "@/lib/api";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { TrendingUp, Loader2, AlertCircle } from "lucide-react";

function ForecastChart({ points, unit }: { points: { period: string; actual?: number | null; low?: number | null; mid?: number | null; high?: number | null; is_forecast?: boolean }[]; unit: string }) {
  // Build recharts data: band needs [low, high] as area
  const data = points.map((p) => ({
    period: p.period.replace(" 20", " '"), // shorten "Jan 2025" → "Jan '25"
    actual: p.actual ?? undefined,
    mid: p.mid ?? undefined,
    band: p.is_forecast && p.low != null && p.high != null ? [p.low, p.high] : undefined,
    is_forecast: p.is_forecast,
  }));

  // Find where forecast starts for the reference line
  const firstForecast = data.find((d) => d.is_forecast)?.period;

  return (
    <ResponsiveContainer width="100%" height={160}>
      <ComposedChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey="period" tick={{ fontSize: 10 }} className="fill-muted-foreground" interval={2} />
        <YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" width={48}
          tickFormatter={(v) => unit === "%" ? `${v}%` : Math.abs(v) >= 1000 ? `${(v/1000).toFixed(0)}k` : `${v}`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--color-card)",
            borderColor: "var(--color-border)",
            borderRadius: "8px",
            fontSize: "11px",
          }}
          formatter={(value: number | number[], name: string) => {
            if (name === "band" && Array.isArray(value)) return [`${value[0].toFixed(1)}–${value[1].toFixed(1)} ${unit}`, "Range"];
            if (name === "actual") return [`${Number(value).toFixed(1)} ${unit}`, "Actual"];
            if (name === "mid") return [`${Number(value).toFixed(1)} ${unit}`, "Forecast (mid)"];
            return [value, name];
          }}
        />
        {firstForecast && (
          <ReferenceLine
            x={firstForecast}
            stroke="var(--color-muted-foreground)"
            strokeDasharray="4 4"
            label={{ value: "Forecast →", position: "insideTopRight", fontSize: 9, fill: "var(--color-muted-foreground)" }}
          />
        )}
        {/* Confidence band (area between low and high) */}
        <Area
          type="monotone"
          dataKey="band"
          fill="var(--color-chart-1)"
          fillOpacity={0.15}
          stroke="none"
          connectNulls
        />
        {/* Actual line */}
        <Line
          type="monotone"
          dataKey="actual"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          dot={{ r: 2, fill: "var(--color-chart-1)" }}
          activeDot={{ r: 4 }}
          connectNulls
        />
        {/* Forecast midline (dashed) */}
        <Line
          type="monotone"
          dataKey="mid"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={{ r: 3, fill: "var(--color-chart-1)", strokeDasharray: "0" }}
          activeDot={{ r: 4 }}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function ForecastPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["kpi-forecast"],
    queryFn: () => getKpiForecast(),
    staleTime: 1000 * 60 * 30, // 30 min — forecasts don't change often
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <TrendingUp size={16} className="text-ac-blue" />
        <h2 className="text-lg font-semibold">3-Month KPI Forecast</h2>
        <span className="text-xs text-muted-foreground ml-1">Powered by Claude · Aug–Oct 2026</span>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-6 justify-center">
          <Loader2 size={14} className="animate-spin" />
          Generating forecast…
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive py-4">
          <AlertCircle size={14} />
          Could not load forecast. Please try again.
        </div>
      )}

      {data?.data?.forecasts && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.data.forecasts.map((fc) => (
            <div key={`${fc.kpi_name}-${fc.kpi_unit}`} className="rounded-lg border bg-card p-3 space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="font-medium text-sm">{fc.kpi_name}</span>
                <span className="text-xs text-muted-foreground">{fc.kpi_unit}</span>
              </div>
              <ForecastChart points={fc.points} unit={fc.kpi_unit} />
              <p className="text-xs text-muted-foreground leading-snug">{fc.insight}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
