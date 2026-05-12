import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useGetDepartmentDetail } from "@/lib/api";
import { useState } from "react";
import type { SubmissionOut } from "@/lib/api";
import { Lock, CheckCircle2, UserCheck, ChevronDown } from "lucide-react";

interface DepartmentDrilldownProps {
  deptId: string | null;
  period?: string | null;
  onClose: () => void;
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

function fillBadge(sub: SubmissionOut) {
  if (sub.kpi_lockin) {
    return <Badge className="bg-blue-500/20 text-blue-600 border-blue-500/30 text-xs gap-1"><Lock size={10} /> Locked</Badge>;
  }
  if (isFilled(sub)) {
    return <Badge className="bg-green-500/20 text-green-600 border-green-500/30 text-xs gap-1"><CheckCircle2 size={10} /> Filled</Badge>;
  }
  return <Badge variant="outline" className="text-xs text-muted-foreground">Empty</Badge>;
}

const DETAIL_FIELDS: { key: keyof SubmissionOut; label: string }[] = [
  { key: "key_drivers_quantitative", label: "Key Drivers (Quantitative)" },
  { key: "key_drivers_qualitative", label: "Key Drivers (Qualitative)" },
  { key: "internal_factors", label: "Internal Factors" },
  { key: "external_factors", label: "External Factors" },
  { key: "oneoff_events", label: "One-off Events" },
  { key: "planned_actions", label: "Planned Actions" },
  { key: "expected_impact", label: "Expected Impact" },
];

const MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function parsePeriod(p: string): number {
  // "Mar 2026" → 202603
  const parts = p.split(" ");
  if (parts.length !== 2) return 0;
  const mi = MONTH_ORDER.indexOf(parts[0]);
  const year = parseInt(parts[1], 10);
  return year * 100 + (mi >= 0 ? mi + 1 : 0);
}

function sortSubmissions(subs: SubmissionOut[]): SubmissionOut[] {
  return [...subs].sort((a, b) => {
    const pa = parsePeriod(a.period);
    const pb = parsePeriod(b.period);
    if (pb !== pa) return pb - pa; // newest period first
    return (a.kpi_number ?? 0) - (b.kpi_number ?? 0); // then by KPI number
  });
}

export function DepartmentDrilldown({ deptId, period, onClose }: DepartmentDrilldownProps) {
  const { data, isLoading } = useGetDepartmentDetail({
    params: { dept_id: deptId ?? "", period },
    query: { enabled: !!deptId },
  });

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const detail = data?.data;
  const sortedSubs = detail ? sortSubmissions(detail.submissions) : [];

  return (
    <Sheet open={!!deptId} onOpenChange={() => { onClose(); setExpandedId(null); }}>
      <SheetContent className="sm:max-w-2xl overflow-hidden flex flex-col">
        <SheetHeader>
          <SheetTitle>{detail?.department?.name ?? "Region"}</SheetTitle>
          <SheetDescription>
            {detail ? `${detail.kpi_count} KPIs | Fill Rate: ${detail.fill_rate}% | Lock Rate: ${detail.lock_rate}%` : "Loading..."}
            {period && ` | ${period}`}
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="space-y-4 mt-4">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        ) : detail ? (
          <ScrollArea className="flex-1 mt-4">
            <div className="space-y-1 pr-4">
              {sortedSubs.map((sub) => {
                const isExpanded = expandedId === sub.id;
                return (
                  <div key={sub.id} className="border rounded-lg overflow-hidden">
                    {/* Row header */}
                    <button
                      type="button"
                      className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/50 transition-colors"
                      onClick={() => setExpandedId(isExpanded ? null : sub.id)}
                    >
                      <ChevronDown
                        size={14}
                        className={`text-muted-foreground shrink-0 transition-transform ${isExpanded ? "rotate-0" : "-rotate-90"}`}
                      />
                      <span className="text-xs text-muted-foreground w-16 shrink-0">{sub.period}</span>
                      <span className="text-xs text-muted-foreground w-4 shrink-0">{sub.kpi_number}</span>
                      <span className="text-sm font-medium flex-1">{sub.kpi_name}</span>
                      <span className="text-xs mr-1">{sub.sentiment_tags || ""}</span>
                      {sub.reviewed_by_gm && (
                        <span className="text-green-600 shrink-0"><UserCheck size={12} /></span>
                      )}
                      {fillBadge(sub)}
                    </button>

                    {/* Expandable detail */}
                    {isExpanded && (
                      <div className="bg-muted/30 px-4 py-3 border-t space-y-2">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="secondary" className="text-xs">{sub.kpi_category}</Badge>
                          {fillBadge(sub)}
                        </div>
                        {DETAIL_FIELDS.map((field) => {
                          const value = sub[field.key] as string;
                          if (!value) return null;
                          return (
                            <div key={field.key}>
                              <span className="text-xs text-muted-foreground">{field.label}</span>
                              <p className="text-sm leading-relaxed">{value}</p>
                            </div>
                          );
                        })}
                        {!isFilled(sub) && (
                          <p className="text-sm text-muted-foreground italic">No qualitative input provided yet.</p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
