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

function computeDeptStats(departments: DepartmentOut[], submissions: SubmissionOut[]): DeptStats[] {
  return departments.map((dept) => {
    const deptSubs = submissions.filter((s) => s.department_id === dept.id);
    const filledCount = deptSubs.filter(isFilled).length;
    const lockedCount = deptSubs.filter((s) => s.kpi_lockin).length;
    const fillPct = deptSubs.length > 0 ? Math.round((filledCount / deptSubs.length) * 100) : 0;
    return { department: dept, kpiCount: deptSubs.length, filledCount, lockedCount, fillPct };
  });
}

function statusColor(fillPct: number): string {
  if (fillPct >= 80) return "border-green-500/50 bg-green-500/5";
  if (fillPct >= 50) return "border-yellow-500/50 bg-yellow-500/5";
  return "border-red-500/50 bg-red-500/5";
}

function statusBadge(fillPct: number) {
  if (fillPct >= 80)
    return <Badge className="bg-green-500/20 text-green-600 border-green-500/30 text-xs">Complete</Badge>;
  if (fillPct >= 50)
    return <Badge className="bg-yellow-500/20 text-yellow-600 border-yellow-500/30 text-xs">In Progress</Badge>;
  return <Badge className="bg-red-500/20 text-red-600 border-red-500/30 text-xs">Pending</Badge>;
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
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  const stats = computeDeptStats(departments, submissions)
    .sort((a, b) => b.fillPct - a.fillPct); // highest fill rate first

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
      {stats.map(({ department, kpiCount, filledCount, lockedCount, fillPct }) => (
        <Card
          key={department.id}
          className={`cursor-pointer transition-all hover:shadow-md ${statusColor(fillPct)}`}
          onClick={() => onSelectDepartment(department.id)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">{department.name}</CardTitle>
              {statusBadge(fillPct)}
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-2">Lead: {department.lead_name}</p>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {filledCount}/{kpiCount} filled &middot; {lockedCount} locked
              </span>
              <span className={`text-lg font-bold ${fillPct >= 80 ? "text-green-500" : fillPct >= 50 ? "text-yellow-500" : "text-red-500"}`}>
                {fillPct}%
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
