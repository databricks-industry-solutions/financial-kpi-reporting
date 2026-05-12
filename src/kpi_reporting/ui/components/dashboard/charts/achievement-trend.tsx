import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { SubmissionOut } from "@/lib/api";

interface AchievementTrendChartProps {
  submissions: SubmissionOut[];
}

export function AchievementTrendChart({ submissions }: AchievementTrendChartProps) {
  // Group by period and compute average achievement
  const byPeriod = new Map<string, { sum: number; count: number }>();
  for (const sub of submissions) {
    const pct = sub.target_value > 0 ? (sub.actual_value / sub.target_value) * 100 : 0;
    const existing = byPeriod.get(sub.period) ?? { sum: 0, count: 0 };
    existing.sum += pct;
    existing.count += 1;
    byPeriod.set(sub.period, existing);
  }

  const periodOrder = [
    "Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025", "May 2025", "Jun 2025",
    "Jul 2025", "Aug 2025", "Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025",
    "Jan 2026", "Feb 2026", "Mar 2026",
  ];

  const chartData = periodOrder
    .filter((p) => byPeriod.has(p))
    .map((period) => {
      const { sum, count } = byPeriod.get(period)!;
      return {
        period,
        achievement: Math.round(sum / count),
      };
    });

  if (chartData.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No trend data available</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey="period" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
        <YAxis tick={{ fontSize: 11 }} domain={[0, 120]} className="fill-muted-foreground" />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--color-card)",
            borderColor: "var(--color-border)",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          formatter={(value: number) => [`${value}%`, "Avg Achievement"]}
        />
        <ReferenceLine y={90} stroke="var(--color-chart-2)" strokeDasharray="5 5" label={{ value: "90% target", position: "insideTopRight", fontSize: 10 }} />
        <Line
          type="monotone"
          dataKey="achievement"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          dot={{ fill: "var(--color-chart-1)", r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
