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
    if (persona.id !== "pnl") navigate({ to: "/home" });
  }, [persona.id, navigate]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="p-4 space-y-4 overflow-auto flex-1 flex flex-col">
        <div>
          <h2 className="text-lg font-semibold">Monthly KPI Reporting</h2>
          <p className="text-sm text-muted-foreground">
            Draft the justification for each KPI, then submit it for your General Manager's review.
          </p>
        </div>
        <KpiReviewTable mode="submit" />
      </div>
    </div>
  );
}
