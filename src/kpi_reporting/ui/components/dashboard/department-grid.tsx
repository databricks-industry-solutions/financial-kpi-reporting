import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetSubmissions, useGetDepartments, type DepartmentOut, type SubmissionOut } from "@/lib/api";

interface DepartmentGridProps {
  period?: string | null;
  onSelectDepartment: (deptId: string) => void;
}

interface DeptStats {
  department: DepartmentOut;
  kpiCount: number;
  filledCount: number;
  lockedCount: number;
  fillPct: number;
  positiveCount: number;
  neutralCount: number;
  cautiousCount: number;
}

function isFilled(sub: SubmissionOut): boolean {
  return !!(
    sub.key_drivers_quantitative ||
    sub.key_drivers_qualitative ||
    sub.internal_factors ||
    sub.external_factors ||
    sub.planned_actions ||
    sub.expected_impact
  );
}

function sentimentBucket(tag: string | null | undefined): "positive" | "neutral" | "cautious" {
  const t = (tag ?? "").toLowerCase();
  if (t === "positive" || t === "on track") return "positive";
  if (t === "negative" || t === "cautious" || t === "at risk") return "cautious";
  return "neutral";
}

function computeDeptStats(departments: DepartmentOut[], submissions: SubmissionOut[]): DeptStats[] {
  return departments.map((dept) => {
    const deptSubs = submissions.filter((s) => s.department_id === dept.id);
    const filledSubs = deptSubs.filter(isFilled);
    const filledCount = filledSubs.length;
    const lockedCount = deptSubs.filter((s) => s.kpi_lockin).length;
    const fillPct = deptSubs.length > 0 ? Math.round((filledCount / deptSubs.length) * 100) : 0;

    // Only count sentiment for filled submissions
    const positiveCount = filledSubs.filter(s => sentimentBucket(s.sentiment_tags) === "positive").length;
    const cautiousCount = filledSubs.filter(s => sentimentBucket(s.sentiment_tags) === "cautious").length;
    const neutralCount = filledSubs.filter(s => sentimentBucket(s.sentiment_tags) === "neutral").length;

    return { department: dept, kpiCount: deptSubs.length, filledCount, lockedCount, fillPct, positiveCount, neutralCount, cautiousCount };
  });
}

function cardBorder(fillPct: number, cautiousCount: number): string {
  if (fillPct >= 80 && cautiousCount === 0) return "border-green-500/50 bg-green-500/5";
  if (fillPct >= 80 && cautiousCount > 0)  return "border-amber-400/50 bg-amber-400/5";
  if (fillPct >= 50) return "border-yellow-500/50 bg-yellow-500/5";
  return "border-red-500/50 bg-red-500/5";
}

function statusBadge(fillPct: number, lockedCount: number, kpiCount: number) {
  if (lockedCount === kpiCount && kpiCount > 0)
    return <Badge className="bg-green-500/20 text-green-600 border-green-500/30 text-xs">Complete</Badge>;
  if (fillPct >= 50)
    return <Badge className="bg-yellow-500/20 text-yellow-600 border-yellow-500/30 text-xs">In Progress</Badge>;
  return <Badge className="bg-red-500/20 text-red-600 border-red-500/30 text-xs">Pending</Badge>;
}

interface MiniBarProps {
  label: string;
  value: number;
  total: number;
  barClass: string;
}

function MiniBar({ label, value, total, barClass }: MiniBarProps) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-0.5">
        <span>{label}</span>
        <span>{value}/{total}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function DepartmentGrid({ period, onSelectDepartment }: DepartmentGridProps) {
  const { data: deptData, isLoading: deptsLoading } = useGetDepartments();
  const { data: subData, isLoading: subsLoading } = useGetSubmissions({
    params: period ? { period } : undefined,
  });

  const isLoading = deptsLoading || subsLoading;
  const departments = deptData?.data ?? [];
  const submissions = subData?.data ?? [];

  if (isLoading) {
    return (
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-36" />
        ))}
      </div>
    );
  }

  const stats = computeDeptStats(departments, submissions)
    .sort((a, b) => b.fillPct - a.fillPct);

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
      {stats.map(({ department, kpiCount, filledCount, lockedCount, fillPct, positiveCount, cautiousCount }) => (
        <Card
          key={department.id}
          className={`cursor-pointer transition-all hover:shadow-md ${cardBorder(fillPct, cautiousCount)}`}
          onClick={() => onSelectDepartment(department.id)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-sm font-semibold leading-tight">{department.name}</CardTitle>
              {statusBadge(fillPct, lockedCount, kpiCount)}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">Lead: {department.lead_name}</p>
          </CardHeader>
          <CardContent className="space-y-2">
            <MiniBar
              label="Filled"
              value={filledCount}
              total={kpiCount}
              barClass="bg-primary"
            />
            <MiniBar
              label="Positive sentiment"
              value={positiveCount}
              total={filledCount || 1}
              barClass="bg-green-500"
            />
            {cautiousCount > 0 && (
              <div className="text-xs text-amber-600 font-medium pt-0.5">
                ⚠ {cautiousCount} cautious / negative
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
