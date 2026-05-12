import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { SubmissionOut } from "@/lib/api";

interface TargetVsActualChartProps {
  submissions: SubmissionOut[];
}

export function TargetVsActualChart({ submissions }: TargetVsActualChartProps) {
  // Deduplicate by kpi_name — take the latest submission per kpi
  const byKpi = new Map<string, SubmissionOut>();
  for (const sub of submissions) {
    const existing = byKpi.get(sub.kpi_name);
    if (!existing || sub.submitted_at > existing.submitted_at) {
      byKpi.set(sub.kpi_name, sub);
    }
  }

  const chartData = Array.from(byKpi.values())
    .slice(0, 10)
    .map((sub) => ({
      name: sub.kpi_name.length > 20 ? sub.kpi_name.slice(0, 18) + "..." : sub.kpi_name,
      Target: sub.target_value,
      Actual: sub.actual_value,
    }));

  if (chartData.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No data available</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} className="fill-muted-foreground" />
        <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--color-card)",
            borderColor: "var(--color-border)",
            borderRadius: "8px",
            fontSize: "12px",
          }}
        />
        <Legend wrapperStyle={{ fontSize: "12px" }} />
        <Bar dataKey="Target" fill="var(--color-chart-3)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Actual" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
