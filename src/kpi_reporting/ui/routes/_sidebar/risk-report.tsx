/**
 * Risk Report — CFO only.
 * AI-generated risk & sentiment deep-dive for a selected reporting period.
 */
import { useState, useEffect } from "react";
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useDemoPersona } from "@/lib/demo-persona";
import { generateRiskReport, publishRiskReport, type RiskReport, type RegionRiskSummary } from "@/lib/api";
import { ShieldAlert, Sparkles, AlertTriangle, CheckCircle2, MinusCircle, TrendingDown, Check, Loader2, FileUp, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/_sidebar/risk-report")({
  validateSearch: (search: Record<string, unknown>) => ({
    period: typeof search.period === "string" ? search.period : undefined,
  }),
  component: () => <RiskReportPage />,
});

// ---- Helpers ---------------------------------------------------------------

const SEVERITY_CONFIG = {
  high:   { label: "High",   classes: "bg-red-500/10 text-red-600 border-red-400/40",    icon: <AlertTriangle size={14} className="text-red-500" /> },
  medium: { label: "Medium", classes: "bg-amber-400/10 text-amber-700 border-amber-400/40", icon: <AlertTriangle size={14} className="text-amber-500" /> },
  low:    { label: "Low",    classes: "bg-blue-400/10 text-blue-700 border-blue-400/40",  icon: <MinusCircle size={14} className="text-blue-500" /> },
};

const SENTIMENT_CONFIG: Record<string, { dot: string; label: string }> = {
  positive: { dot: "bg-green-500",  label: "Positive" },
  neutral:  { dot: "bg-slate-400",  label: "Neutral"  },
  cautious: { dot: "bg-amber-400",  label: "Cautious" },
  negative: { dot: "bg-red-500",    label: "Negative" },
};

const RISK_LEVEL_BORDER: Record<string, string> = {
  none:   "border-green-400/40 bg-green-500/5",
  low:    "border-blue-400/30 bg-blue-500/5",
  medium: "border-amber-400/40 bg-amber-400/5",
  high:   "border-red-400/40 bg-red-500/5",
};

const KPI_ORDER = ["Revenue Growth", "Operating Margin", "DSO", "OPEX Ratio", "Free Cash Flow"];

function SentimentDot({ sentiment }: { sentiment: string }) {
  const cfg = SENTIMENT_CONFIG[sentiment?.toLowerCase()] ?? SENTIMENT_CONFIG.neutral;
  return <span className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${cfg.dot}`} title={cfg.label} />;
}

// ---- Sentiment Heatmap -----------------------------------------------------

function SentimentHeatmap({ regionSummaries }: { regionSummaries: RegionRiskSummary[] }) {
  const kpis = KPI_ORDER;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            <th className="text-left py-1.5 pr-3 font-medium text-muted-foreground w-40">Region</th>
            {kpis.map(k => (
              <th key={k} className="text-center py-1.5 px-2 font-medium text-muted-foreground min-w-[90px]">{k}</th>
            ))}
            <th className="text-center py-1.5 px-2 font-medium text-muted-foreground">Overall</th>
          </tr>
        </thead>
        <tbody>
          {regionSummaries.map(cc => (
            <tr key={cc.region_name} className="border-t border-border/40">
              <td className="py-2 pr-3 font-medium text-sm">{cc.region_name}</td>
              {kpis.map(kpi => {
                const sentiment = (cc.kpi_sentiments?.[kpi] ?? "neutral").toLowerCase();
                const cfg = SENTIMENT_CONFIG[sentiment] ?? SENTIMENT_CONFIG.neutral;
                return (
                  <td key={kpi} className="text-center py-2 px-2">
                    <div className="flex items-center justify-center gap-1">
                      <span className={`inline-block w-3 h-3 rounded-sm ${cfg.dot}`} />
                      <span className="text-muted-foreground">{cfg.label}</span>
                    </div>
                  </td>
                );
              })}
              <td className="text-center py-2 px-2">
                <div className="flex items-center justify-center gap-1">
                  <SentimentDot sentiment={cc.overall_sentiment ?? "neutral"} />
                  <span className="text-muted-foreground capitalize">{cc.overall_sentiment ?? "neutral"}</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 pt-2 border-t border-border/30">
        {Object.entries(SENTIMENT_CONFIG).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className={`inline-block w-2.5 h-2.5 rounded-sm ${cfg.dot}`} />
            {cfg.label}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Main page -------------------------------------------------------------

export default function RiskReportPage() {
  const { persona } = useDemoPersona();
  const navigate = useNavigate();

  useEffect(() => {
    if (persona.id !== "cfo") navigate({ to: "/home" });
  }, [persona.id, navigate]);

  const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const periods = (() => {
    const result: string[] = [];
    const now = new Date();
    for (let d = new Date(2025, 0); d <= now; d.setMonth(d.getMonth() + 1)) {
      result.push(`${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`);
    }
    return result.reverse(); // newest first
  })();

  const { period: searchPeriod } = useSearch({ from: "/_sidebar/risk-report" });
  const [period, setPeriod] = useState<string>(searchPeriod ?? periods[0] ?? "");
  const [report, setReport] = useState<RiskReport | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [progressStep, setProgressStep] = useState(0);

  // Publish-to-Confluence state
  const [publishState, setPublishState] = useState<"idle" | "publishing" | "done" | "error">("idle");
  const [publishUrl, setPublishUrl] = useState<string>("");
  const [publishError, setPublishError] = useState<string>("");

  const PROGRESS_STEPS = [
    "Loading KPI submissions from Lakebase…",
    "Aggregating sentiment across regions…",
    "Identifying top risks and cross-cutting patterns…",
    "Drafting the executive summary…",
  ];

  const generate = async () => {
    if (!period) return;
    setState("loading");
    setReport(null);
    setErrorMsg("");
    setProgressStep(0);
    setPublishState("idle");
    setPublishUrl("");

    // Advance the progress messages while the request is in flight.
    const timers: ReturnType<typeof setTimeout>[] = [];
    PROGRESS_STEPS.forEach((_, i) => {
      if (i > 0) timers.push(setTimeout(() => setProgressStep(i), i * 2500));
    });

    try {
      const result = await generateRiskReport({ period });
      setReport(result.data);
      setState("done");
    } catch (err: unknown) {
      // Extract detail message from ApiError if available
      const detail = err && typeof err === "object" && "body" in err
        ? (err as { body?: { detail?: string } }).body?.detail
        : null;
      setErrorMsg(detail || String(err));
      setState("error");
    } finally {
      timers.forEach(clearTimeout);
    }
  };

  const publish = async () => {
    if (!report) return;
    setPublishState("publishing");
    setPublishError("");
    try {
      const result = await publishRiskReport(report);
      setPublishUrl(result.data.confluence_page_url);
      setPublishState("done");
    } catch (err) {
      setPublishError(String(err));
      setPublishState("error");
    }
  };

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 px-6 py-4 border-b shrink-0">
        <div className="flex items-center gap-2">
          <ShieldAlert size={18} className="text-red-500" />
          <h1 className="text-lg font-semibold">Risk & Sentiment Report</h1>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-36 h-8 text-sm">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              {periods.map(p => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {state === "done" && (
            publishState === "done" ? (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 h-8 text-green-700 border-green-400/40"
                onClick={() => window.open(publishUrl, "_blank")}
              >
                <ExternalLink size={13} /> View in Confluence
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 h-8"
                onClick={publish}
                disabled={publishState === "publishing"}
              >
                {publishState === "publishing" ? (
                  <><Loader2 size={13} className="animate-spin" /> Publishing…</>
                ) : (
                  <><FileUp size={13} /> Publish to Confluence</>
                )}
              </Button>
            )
          )}
          <Button
            size="sm"
            className="gap-1.5 h-8"
            onClick={generate}
            disabled={!period || state === "loading"}
          >
            {state === "loading" ? (
              <><span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" /> Analysing…</>
            ) : (
              <><Sparkles size={13} /> {state === "done" ? "Regenerate" : "Generate Report"}</>
            )}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6 max-w-5xl mx-auto w-full">

        {/* Idle state */}
        {state === "idle" && (
          <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
            <ShieldAlert size={40} className="opacity-20" />
            <p className="text-sm">Select a period and click Generate Report to run the AI risk analysis.</p>
          </div>
        )}

        {/* Loading */}
        {state === "loading" && (
          <div className="space-y-6">
            {/* Live progress checklist */}
            <Card className="border-purple-400/30 bg-purple-500/5">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Loader2 size={16} className="text-purple-500 animate-spin" />
                  <span className="text-sm font-medium text-foreground">
                    Generating risk report for {period}…
                  </span>
                </div>
                <ul className="space-y-2.5">
                  {PROGRESS_STEPS.map((label, i) => {
                    const isDone = i < progressStep;
                    const isActive = i === progressStep;
                    return (
                      <li key={i} className="flex items-center gap-2.5 text-sm">
                        {isDone ? (
                          <Check size={15} className="text-green-500 shrink-0" />
                        ) : isActive ? (
                          <Loader2 size={15} className="text-purple-500 animate-spin shrink-0" />
                        ) : (
                          <span className="w-[15px] h-[15px] rounded-full border border-muted-foreground/30 shrink-0" />
                        )}
                        <span className={isDone ? "text-muted-foreground line-through" : isActive ? "text-foreground" : "text-muted-foreground/60"}>
                          {label}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
            {/* Skeleton preview of the layout */}
            <Skeleton className="h-24 w-full rounded-xl" />
            <div className="grid grid-cols-3 gap-4">
              {[1,2,3].map(i => <Skeleton key={i} className="h-32 rounded-xl" />)}
            </div>
          </div>
        )}

        {/* Error */}
        {state === "error" && (
          <div className="text-destructive text-sm p-4 rounded-lg border border-destructive/30 bg-destructive/5">
            {errorMsg}
          </div>
        )}

        {/* Report */}
        {state === "done" && report && (
          <>
            {/* Publish result banners */}
            {publishState === "done" && (
              <div className="text-sm p-3 rounded-lg border border-green-400/40 bg-green-500/5 text-green-700 flex items-center gap-2">
                <CheckCircle2 size={15} /> Published to Confluence.
                <a href={publishUrl} target="_blank" rel="noreferrer" className="underline font-medium">Open page</a>
              </div>
            )}
            {publishState === "error" && (
              <div className="text-sm p-3 rounded-lg border border-destructive/30 bg-destructive/5 text-destructive">
                Failed to publish: {publishError}
              </div>
            )}

            {/* Executive Summary */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Sparkles size={14} className="text-purple-500" />
                  Executive Summary — {report.period}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-foreground">{report.executive_summary}</p>
              </CardContent>
            </Card>

            {/* Top Risks */}
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <TrendingDown size={15} className="text-red-500" /> Top Risks
              </h2>
              <div className="space-y-3">
                {report.top_risks.map(risk => {
                  const cfg = SEVERITY_CONFIG[risk.severity as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.low;
                  return (
                    <Card key={risk.rank} className={`border ${cfg.classes}`}>
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="flex items-center gap-1.5 mt-0.5 shrink-0">
                            {cfg.icon}
                            <Badge variant="outline" className={`text-xs ${cfg.classes}`}>{cfg.label}</Badge>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm text-foreground">{risk.title}</p>
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed italic">"{risk.evidence}"</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {(risk.affected_regions ?? []).map(cc => (
                                <Badge key={cc} variant="secondary" className="text-xs">{cc}</Badge>
                              ))}
                              {(risk.affected_kpis ?? []).map(kpi => (
                                <Badge key={kpi} variant="outline" className="text-xs">{kpi}</Badge>
                              ))}
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">
                              <span className="font-medium text-foreground">Recommended: </span>
                              {risk.recommended_action}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Sentiment Heatmap */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Sentiment Heatmap — Region × KPI</CardTitle>
              </CardHeader>
              <CardContent>
                <SentimentHeatmap regionSummaries={report.region_summaries} />
              </CardContent>
            </Card>

            {/* Region summaries */}
            <div>
              <h2 className="text-sm font-semibold text-foreground mb-3">Region Summaries</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {report.region_summaries.map(cc => (
                  <Card key={cc.region_name} className={`border ${RISK_LEVEL_BORDER[cc.risk_level ?? "low"] ?? RISK_LEVEL_BORDER.low}`}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-medium text-sm">{cc.region_name}</span>
                        <div className="flex items-center gap-1.5">
                          <SentimentDot sentiment={cc.overall_sentiment ?? "neutral"} />
                          <span className="text-xs text-muted-foreground capitalize">{cc.overall_sentiment ?? "neutral"}</span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{cc.headline}</p>
                      {cc.risk_level !== "none" && (
                        <div className="mt-2">
                          <Badge variant="outline" className={`text-xs ${
                            cc.risk_level === "high" ? "text-red-600 border-red-400/40" :
                            cc.risk_level === "medium" ? "text-amber-700 border-amber-400/40" :
                            "text-blue-700 border-blue-400/40"
                          }`}>
                            {cc.risk_level} risk
                          </Badge>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Patterns + Outlook */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">Cross-Cutting Patterns</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">{report.cross_cutting_patterns}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-green-500" /> Outlook
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">{report.outlook}</p>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
