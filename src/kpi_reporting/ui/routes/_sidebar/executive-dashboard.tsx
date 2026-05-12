import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { toast } from "sonner";
import { BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { DepartmentGrid } from "@/components/dashboard/department-grid";
import { DepartmentDrilldown } from "@/components/dashboard/department-drilldown";
import { GenieChatPanel } from "@/components/dashboard/genie-chat";
import { useGetDashboardSummary, usePublishDashboardSummary } from "@/lib/api";

export const Route = createFileRoute("/_sidebar/executive-dashboard")({
  component: () => <ExecutiveDashboardPage />,
});

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function buildPeriods(): { value: string; label: string }[] {
  const now = new Date();
  const periods: { value: string; label: string }[] = [
    { value: "__all__", label: "All Periods" },
  ];
  // Generate months from Jan 2025 up to current month, newest first
  const start = new Date(2025, 0); // Jan 2025
  const entries: { value: string; label: string }[] = [];
  for (let d = new Date(start); d <= now; d.setMonth(d.getMonth() + 1)) {
    const label = `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
    entries.push({ value: label, label });
  }
  entries.reverse(); // newest first
  return [...periods, ...entries];
}

const PERIODS = buildPeriods();

function ExecutiveDashboardPage() {
  const [period, setPeriod] = useState<string>("__all__");
  const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);

  const activePeriod = period === "__all__" ? null : period;

  const { data: summaryData, isLoading: summaryLoading } = useGetDashboardSummary({
    params: activePeriod ? { period: activePeriod } : undefined,
  });
  const dashboardPublishMutation = usePublishDashboardSummary();

  const handlePublishDashboard = () => {
    dashboardPublishMutation.mutate(
      { period: activePeriod },
      {
        onSuccess: (result) => {
          toast.success("Dashboard summary published to Confluence", {
            action: {
              label: "Open",
              onClick: () => window.open(result.data.confluence_page_url, "_blank"),
            },
          });
        },
        onError: (err) => {
          toast.error(`Failed to publish: ${err.message}`);
        },
      },
    );
  };

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="p-4 space-y-6">
        {/* Header + Filter */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Monthly KPI Report — Overview</h1>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePublishDashboard}
              disabled={dashboardPublishMutation.isPending || summaryLoading}
              className="gap-1.5"
            >
              <BookOpen size={14} />
              {dashboardPublishMutation.isPending ? "Publishing..." : "Publish to Confluence"}
            </Button>
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PERIODS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Summary Cards */}
        <SummaryCards summary={summaryData?.data} isLoading={summaryLoading} />

        {/* Department Grid */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Region Overview</h2>
          <DepartmentGrid
            period={activePeriod}
            onSelectDepartment={setSelectedDeptId}
          />
        </div>

        {/* Genie Chat */}
        <GenieChatPanel />
      </div>

      {/* Department Drilldown Sheet */}
      <DepartmentDrilldown
        deptId={selectedDeptId}
        period={activePeriod}
        onClose={() => setSelectedDeptId(null)}
      />
    </div>
  );
}
