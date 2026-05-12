import { createFileRoute } from "@tanstack/react-router";
import { KpiReviewTable } from "@/components/kpi/submission-history";

export const Route = createFileRoute("/_sidebar/kpi-submission")({
  component: () => <KpiSubmissionPage />,
});

function KpiSubmissionPage() {
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="p-4 space-y-4 overflow-auto flex-1 flex flex-col">
        <h2 className="text-lg font-semibold">Monthly KPI Reporting</h2>
        <KpiReviewTable />
      </div>
    </div>
  );
}
