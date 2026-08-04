import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAiBiDashboardUrl } from "@/lib/api";
import { BarChart2 } from "lucide-react";
import { useDemoPersona } from "@/lib/demo-persona";

export const Route = createFileRoute("/_sidebar/analytics-dashboard")({
  component: AnalyticsDashboard,
});

function AnalyticsDashboard() {
  const { persona } = useDemoPersona();
  const navigate = useNavigate();
  useEffect(() => {
    if (persona.id !== "cfo") navigate({ to: "/home" });
  }, [persona.id, navigate]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["aibi-dashboard-url"],
    queryFn: () => getAiBiDashboardUrl(),
    staleTime: Infinity,
  });

  return (
    <div className="flex flex-col flex-1 overflow-hidden w-full">
      <div className="flex items-center gap-2 px-6 py-4 border-b shrink-0">
        <BarChart2 size={18} className="text-ac-blue" />
        <h1 className="text-lg font-semibold">Analytics Dashboard</h1>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {isLoading && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Loading dashboard…
          </div>
        )}
        {error && (
          <div className="flex items-center justify-center h-full text-destructive text-sm">
            Could not load dashboard URL. Make sure the app is configured with a valid AI/BI dashboard ID.
          </div>
        )}
        {data?.data?.url && (
          <iframe
            src={data.data.url}
            title="KPI Analytics Dashboard"
            className="flex-1 w-full h-full border-0"
            allow="fullscreen"
          />
        )}
      </div>
    </div>
  );
}
