import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ClipboardList, CheckCircle2, Lock, Building2 } from "lucide-react";
import type { DashboardSummary } from "@/lib/api";

interface SummaryCardsProps {
  summary: DashboardSummary | undefined;
  isLoading: boolean;
}

export function SummaryCards({ summary, isLoading }: SummaryCardsProps) {
  const fillPct = summary && summary.total_entries > 0
    ? Math.round((summary.filled_entries / summary.total_entries) * 100)
    : 0;

  const cards = [
    {
      title: "Total KPI Entries",
      value: summary ? summary.total_entries.toLocaleString() : "—",
      icon: <ClipboardList className="h-4 w-4 text-muted-foreground" />,
      description: "5 KPIs per CC per month",
    },
    {
      title: "Filled In",
      value: summary ? `${summary.filled_entries} (${fillPct}%)` : "—",
      icon: <CheckCircle2 className="h-4 w-4 text-muted-foreground" />,
      description: "KPIs with qualitative input",
    },
    {
      title: "Locked In",
      value: summary ? summary.locked_entries.toLocaleString() : "—",
      icon: <Lock className="h-4 w-4 text-muted-foreground" />,
      description: "KPIs finalized and locked",
    },
    {
      title: "Centers Reporting",
      value: summary ? summary.departments_reporting.toString() : "—",
      icon: <Building2 className="h-4 w-4 text-muted-foreground" />,
      description: "CCs with at least one filled KPI",
    },
  ];

  return (
    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
            {card.icon}
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">{card.value}</div>
                <p className="text-xs text-muted-foreground">{card.description}</p>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
