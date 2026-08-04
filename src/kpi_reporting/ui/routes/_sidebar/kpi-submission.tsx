import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { KpiReviewTable } from "@/components/kpi/submission-history";
import { useDemoPersona } from "@/lib/demo-persona";

export const Route = createFileRoute("/_sidebar/kpi-submission")({
  component: () => <KpiSubmissionPage />,
});

function KpiSubmissionPage() {
  const { persona } = useDemoPersona();
  const navigate = useNavigate();
  useEffect(() => {
    if (persona.id !== "gm") navigate({ to: "/home" });
  }, [persona.id, navigate]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="p-4 space-y-4 overflow-auto flex-1 flex flex-col">
        <h2 className="text-lg font-semibold">Monthly KPI Reporting</h2>
        <KpiReviewTable />
      </div>
    </div>
  );
}
