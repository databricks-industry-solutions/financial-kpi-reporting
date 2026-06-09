import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ExternalLink, BookOpen, Pencil, Lock, Unlock, UserCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetSubmissions, useUpdateSubmission, usePublishToConfluence,
  usePublishSubmissionsSummary, getSubmissionsKey, type SubmissionOut,
} from "@/lib/api";
import { usePersona } from "@/lib/persona";

const ALL = "__all__";

const MONTH_ORDER: Record<string, number> = {
  Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6,
  Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12,
};

/** Format a KPI value with its unit for display. Large EUR values become MEUR. */
function formatKpiValue(value: number | null | undefined, unit: string): string {
  if (value == null) return "—";
  if (unit === "EUR" && Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)} MEUR`;
  }
  if (unit === "EUR") {
    return `${value.toLocaleString()} EUR`;
  }
  return `${value} ${unit}`;
}

function periodSortKey(period: string): number {
  const parts = period.split(" ");
  if (parts.length !== 2) return 0;
  const month = MONTH_ORDER[parts[0]] ?? 0;
  const year = parseInt(parts[1], 10) || 0;
  return year * 100 + month;
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
    return <Badge className="bg-green-500/20 text-green-600 border-green-500/30 text-xs">Filled</Badge>;
  }
  return <Badge variant="outline" className="text-xs text-muted-foreground">Empty</Badge>;
}

function sentimentColor(sentiment: string): string {
  if (sentiment === "Positive") return "text-green-600";
  if (sentiment === "Cautious") return "text-yellow-600";
  return "text-muted-foreground";
}

interface EditFormState {
  key_drivers_quantitative: string;
  key_drivers_qualitative: string;
  internal_factors: string;
  external_factors: string;
  oneoff_events: string;
  planned_actions: string;
  expected_impact: string;
  sentiment_tags: string;
  kpi_lockin: boolean;
  reviewed_by_gm: string;
}

export function KpiReviewTable() {
  const { data, isLoading } = useGetSubmissions();
  const queryClient = useQueryClient();
  const updateMutation = useUpdateSubmission();
  const publishMutation = usePublishToConfluence();
  const summaryMutation = usePublishSubmissionsSummary();
  const { persona } = usePersona();

  const [filterPeriod, setFilterPeriod] = useState(ALL);
  const [filterKpi, setFilterKpi] = useState(ALL);
  const [filterStatus, setFilterStatus] = useState(ALL);

  const [sheetMode, setSheetMode] = useState<"edit" | "detail" | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<SubmissionOut | null>(null);
  const [form, setForm] = useState<EditFormState>({
    key_drivers_quantitative: "",
    key_drivers_qualitative: "",
    internal_factors: "",
    external_factors: "",
    oneoff_events: "",
    planned_actions: "",
    expected_impact: "",
    sentiment_tags: "",
    kpi_lockin: false,
    reviewed_by_gm: "",
  });

  const allSubmissions = useMemo(() => {
    if (persona.isExecutive || !persona.deptName) return data?.data ?? [];
    return (data?.data ?? []).filter((s) => s.department_name === persona.deptName);
  }, [data, persona.deptName, persona.isExecutive]);

  const periods = useMemo(() => {
    const set = new Set(allSubmissions.map((s) => s.period));
    return Array.from(set).sort((a, b) => periodSortKey(b) - periodSortKey(a));
  }, [allSubmissions]);

  const kpiNames = useMemo(() => {
    const set = new Set(allSubmissions.map((s) => s.kpi_name));
    return Array.from(set).sort();
  }, [allSubmissions]);

  const STATUS_OPTIONS = ["Filled", "Empty", "Locked"];

  const submissions = useMemo(() => {
    let result = allSubmissions;
    if (filterPeriod !== ALL) result = result.filter((s) => s.period === filterPeriod);
    if (filterKpi !== ALL) result = result.filter((s) => s.kpi_name === filterKpi);
    if (filterStatus !== ALL) {
      result = result.filter((s) => {
        if (filterStatus === "Locked") return s.kpi_lockin;
        if (filterStatus === "Filled") return !s.kpi_lockin && isFilled(s);
        return !s.kpi_lockin && !isFilled(s); // Empty
      });
    }
    return result.sort((a, b) => {
      const pa = periodSortKey(a.period);
      const pb = periodSortKey(b.period);
      if (pa !== pb) return pb - pa;
      return a.kpi_number - b.kpi_number;
    });
  }, [allSubmissions, filterPeriod, filterKpi, filterStatus]);

  const openEditSheet = (sub: SubmissionOut, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedSubmission(sub);
    setForm({
      key_drivers_quantitative: sub.key_drivers_quantitative,
      key_drivers_qualitative: sub.key_drivers_qualitative,
      internal_factors: sub.internal_factors,
      external_factors: sub.external_factors,
      oneoff_events: sub.oneoff_events,
      planned_actions: sub.planned_actions,
      expected_impact: sub.expected_impact,
      sentiment_tags: sub.sentiment_tags,
      kpi_lockin: sub.kpi_lockin,
      reviewed_by_gm: sub.reviewed_by_gm,
    });
    setSheetMode("edit");
  };

  const openDetailSheet = (sub: SubmissionOut) => {
    setSelectedSubmission(sub);
    setSheetMode("detail");
  };

  const closeSheet = () => {
    setSheetMode(null);
    setSelectedSubmission(null);
  };

  const handleSave = () => {
    if (!selectedSubmission) return;
    updateMutation.mutate(
      {
        params: { sub_id: selectedSubmission.id },
        data: { ...form },
      },
      {
        onSuccess: () => {
          toast.success("KPI updated successfully");
          queryClient.invalidateQueries({ queryKey: getSubmissionsKey() });
          closeSheet();
        },
        onError: (err) => {
          toast.error(`Failed to save: ${err.message}`);
        },
      },
    );
  };

  const handlePublish = (subId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    publishMutation.mutate(
      { params: { sub_id: subId } },
      {
        onSuccess: (result) => {
          toast.success("Published to Confluence", {
            action: {
              label: "Open",
              onClick: () => window.open(result.data.confluence_page_url, "_blank"),
            },
          });
          queryClient.invalidateQueries({ queryKey: getSubmissionsKey() });
        },
        onError: (err) => {
          toast.error(`Failed to publish: ${err.message}`);
        },
      },
    );
  };

  const updateField = (field: keyof EditFormState, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  const SENTIMENT_OPTIONS = ["Positive", "Neutral", "Cautious"];

  const EDITABLE_FIELDS: { key: keyof EditFormState; label: string; rows: number }[] = [
    { key: "key_drivers_quantitative", label: "Key Drivers (Quantitative)", rows: 2 },
    { key: "key_drivers_qualitative", label: "Key Drivers (Qualitative)", rows: 2 },
    { key: "internal_factors", label: "Internal Factors", rows: 2 },
    { key: "external_factors", label: "External Factors", rows: 2 },
    { key: "oneoff_events", label: "One-off Events / Exceptions", rows: 2 },
    { key: "planned_actions", label: "Planned Actions", rows: 2 },
    { key: "expected_impact", label: "Expected Impact", rows: 2 },
  ];

  const DETAIL_FIELDS: { key: keyof SubmissionOut; label: string }[] = [
    { key: "key_drivers_quantitative", label: "Key Drivers (Quantitative)" },
    { key: "key_drivers_qualitative", label: "Key Drivers (Qualitative)" },
    { key: "internal_factors", label: "Internal Factors" },
    { key: "external_factors", label: "External Factors" },
    { key: "oneoff_events", label: "One-off Events / Exceptions" },
    { key: "planned_actions", label: "Planned Actions" },
    { key: "expected_impact", label: "Expected Impact" },
  ];

  return (
    <>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 px-1 pb-3">
        <Select value={filterPeriod} onValueChange={setFilterPeriod}>
          <SelectTrigger className="w-[140px] h-8 text-xs">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All Periods</SelectItem>
            {periods.map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterKpi} onValueChange={setFilterKpi}>
          <SelectTrigger className="w-[160px] h-8 text-xs">
            <SelectValue placeholder="KPI" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All KPIs</SelectItem>
            {kpiNames.map((k) => (
              <SelectItem key={k} value={k}>{k}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[120px] h-8 text-xs">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All Status</SelectItem>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {(filterPeriod !== ALL || filterKpi !== ALL || filterStatus !== ALL) && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs text-muted-foreground"
            onClick={() => { setFilterPeriod(ALL); setFilterKpi(ALL); setFilterStatus(ALL); }}
          >
            Clear filters
          </Button>
        )}

        <span className="ml-auto text-xs text-muted-foreground">
          {submissions.length} KPI{submissions.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* KPI Table */}
      <div className="overflow-auto flex-1">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Period</TableHead>
              <TableHead>#</TableHead>
              <TableHead>KPI Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="text-right">Value</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Sentiment</TableHead>
              <TableHead>GM Review</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {submissions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                  No KPIs match the current filters.
                </TableCell>
              </TableRow>
            ) : (
              submissions.map((sub) => (
                <TableRow
                  key={sub.id}
                  className="cursor-pointer"
                  onClick={() => openDetailSheet(sub)}
                >
                  <TableCell className="font-medium">{sub.period}</TableCell>
                  <TableCell className="text-muted-foreground">{sub.kpi_number}</TableCell>
                  <TableCell>{sub.kpi_name}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-xs">{sub.kpi_category}</Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {sub.kpi_value != null ? formatKpiValue(sub.kpi_value, sub.kpi_unit) : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell>{fillBadge(sub)}</TableCell>
                  <TableCell className={sentimentColor(sub.sentiment_tags)}>
                    {sub.sentiment_tags || "—"}
                  </TableCell>
                  <TableCell>
                    {sub.reviewed_by_gm ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-600">
                        <UserCheck size={12} /> {sub.reviewed_by_gm.split(" ")[0]}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {!sub.kpi_lockin ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => openEditSheet(sub, e)}
                        className="text-xs h-7 gap-1"
                      >
                        <Pencil size={14} /> Edit
                      </Button>
                    ) : sub.confluence_page_url ? (
                      <a
                        href={sub.confluence_page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-ac-blue hover:underline inline-flex items-center gap-1 text-xs"
                      >
                        <ExternalLink size={14} /> View
                      </a>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handlePublish(sub.id, e)}
                        disabled={publishMutation.isPending}
                        className="text-xs h-7"
                      >
                        <BookOpen size={14} /> Publish
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Publish Summary */}
      {submissions.length > 0 && persona.deptName && (
        <div className="flex items-center justify-end px-1 pt-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              summaryMutation.mutate(
                {
                  department_name: persona.deptName as string,
                  period: filterPeriod !== ALL ? filterPeriod : null,
                },
                {
                  onSuccess: (result) => {
                    toast.success("Summary published to Confluence", {
                      action: {
                        label: "Open",
                        onClick: () => window.open(result.data.confluence_page_url, "_blank"),
                      },
                    });
                  },
                  onError: (err) => {
                    toast.error(`Failed to publish summary: ${err.message}`);
                  },
                },
              );
            }}
            disabled={summaryMutation.isPending}
            className="gap-1.5"
          >
            <BookOpen size={14} />
            {summaryMutation.isPending ? "Publishing..." : "Publish Summary to Confluence"}
          </Button>
        </div>
      )}

      {/* Edit Sheet */}
      <Sheet open={sheetMode === "edit"} onOpenChange={closeSheet}>
        <SheetContent className="sm:max-w-lg overflow-auto">
          <SheetHeader>
            <SheetTitle>Edit KPI — {selectedSubmission?.kpi_name}</SheetTitle>
            <SheetDescription>
              {selectedSubmission?.department_name} &middot; {selectedSubmission?.period} &middot; #{selectedSubmission?.kpi_number}
            </SheetDescription>
          </SheetHeader>
          {selectedSubmission && (
            <div className="mt-6 space-y-4">
              {EDITABLE_FIELDS.map((field) => (
                <div key={field.key} className="space-y-1.5">
                  <Label htmlFor={field.key} className="text-xs font-medium">{field.label}</Label>
                  <Textarea
                    id={field.key}
                    value={form[field.key] as string}
                    onChange={(e) => updateField(field.key, e.target.value)}
                    placeholder={`Enter ${field.label.toLowerCase()}...`}
                    rows={field.rows}
                    className="text-sm"
                  />
                </div>
              ))}

              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Sentiment</Label>
                <Select value={form.sentiment_tags || "Neutral"} onValueChange={(v) => updateField("sentiment_tags", v)}>
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SENTIMENT_OPTIONS.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-4 pt-2">
                <Button
                  variant={form.kpi_lockin ? "default" : "outline"}
                  size="sm"
                  className="gap-1.5"
                  onClick={() => updateField("kpi_lockin", !form.kpi_lockin)}
                >
                  {form.kpi_lockin ? <Lock size={14} /> : <Unlock size={14} />}
                  {form.kpi_lockin ? "Locked In" : "Lock In"}
                </Button>
                <Button
                  variant={form.reviewed_by_gm ? "default" : "outline"}
                  size="sm"
                  className="gap-1.5"
                  onClick={() => updateField("reviewed_by_gm", form.reviewed_by_gm ? "" : persona.leadName)}
                >
                  <UserCheck size={14} />
                  {form.reviewed_by_gm ? "GM Reviewed" : "Mark GM Reviewed"}
                </Button>
              </div>

              <Button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="w-full mt-4"
              >
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Detail Sheet — read-only */}
      <Sheet open={sheetMode === "detail"} onOpenChange={closeSheet}>
        <SheetContent className="sm:max-w-lg overflow-auto">
          <SheetHeader>
            <SheetTitle>{selectedSubmission?.kpi_name}</SheetTitle>
            <SheetDescription>
              {selectedSubmission?.department_name} &middot; {selectedSubmission?.period} &middot; #{selectedSubmission?.kpi_number}
            </SheetDescription>
          </SheetHeader>
          {selectedSubmission && (
            <div className="mt-6 space-y-4">
              {selectedSubmission.kpi_value != null && (
                <div className="text-2xl font-bold tabular-nums">
                  {formatKpiValue(selectedSubmission.kpi_value, selectedSubmission.kpi_unit)}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">{selectedSubmission.kpi_category}</Badge>
                {fillBadge(selectedSubmission)}
                {selectedSubmission.sentiment_tags && (
                  <Badge variant="outline" className={`text-xs ${sentimentColor(selectedSubmission.sentiment_tags)}`}>
                    {selectedSubmission.sentiment_tags}
                  </Badge>
                )}
              </div>

              {DETAIL_FIELDS.map((field) => {
                const value = selectedSubmission[field.key] as string;
                return (
                  <div key={field.key}>
                    <span className="text-xs text-muted-foreground">{field.label}</span>
                    <p className="mt-0.5 text-sm leading-relaxed bg-muted/50 p-2.5 rounded-lg min-h-[2rem]">
                      {value || <span className="text-muted-foreground italic">Not provided</span>}
                    </p>
                  </div>
                );
              })}

              <div className="grid grid-cols-2 gap-4 pt-2 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground">Locked In</span>
                  <p className="font-medium">{selectedSubmission.kpi_lockin ? "Yes" : "No"}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Reviewed by GM</span>
                  <p className="font-medium">{selectedSubmission.reviewed_by_gm || "Not yet"}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Submitted By</span>
                  <p className="font-medium">{selectedSubmission.submitted_by}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Last Updated</span>
                  <p className="font-medium">{new Date(selectedSubmission.updated_at).toLocaleDateString()}</p>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
