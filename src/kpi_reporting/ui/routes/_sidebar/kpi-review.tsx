import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { KpiReviewTable } from "@/components/kpi/submission-history";
import { useDemoPersona } from "@/lib/demo-persona";

export const Route = createFileRoute("/_sidebar/kpi-review")({
  component: () => <KpiReviewPage />,
});

function KpiReviewPage() {
  const { persona } = useDemoPersona();
  const navigate = useNavigate();
  useEffect(() => {
    if (persona.id !== "gm") navigate({ to: "/home" });
  }, [persona.id, navigate]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="p-4 space-y-4 overflow-auto flex-1 flex flex-col">
        <div>
          <h2 className="text-lg font-semibold">KPI Review</h2>
          <p className="text-sm text-muted-foreground">
            Review the KPI justifications your P&amp;L manager submitted, then approve them or send them back.
          </p>
        </div>
        <KpiReviewTable mode="review" />
      </div>
    </div>
  );
}
