/**
 * NarrativePanel — shown on the Executive Dashboard.
 * Generates an AI executive narrative for the selected period.
 */
import { useState } from "react";
import { Sparkles, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { agentNarrative } from "@/lib/api";

interface NarrativePanelProps {
  period: string | null; // null = "All Periods"
}

// Very minimal markdown → JSX: just handle ## headers and bullet points
function renderMarkdown(text: string) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    if (line.startsWith("## ")) {
      return <h3 key={i} className="font-semibold text-sm mt-4 mb-1 text-foreground">{line.slice(3)}</h3>;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      return <li key={i} className="ml-4 text-sm leading-relaxed list-disc">{line.slice(2)}</li>;
    }
    if (line.trim() === "") {
      return <div key={i} className="h-1" />;
    }
    return <p key={i} className="text-sm leading-relaxed">{line}</p>;
  });
}

export function NarrativePanel({ period }: NarrativePanelProps) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [narrative, setNarrative] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const effectivePeriod = period ?? "All Periods";

  const generate = async () => {
    if (!period) return;

    setState("loading");
    setNarrative("");
    setErrorMsg("");
    setCollapsed(false);

    try {
      const result = await agentNarrative({ period });
      const text = result?.data?.narrative ?? "";
      setNarrative(text);
      setState("done");
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "body" in err
        ? (err as { body?: { detail?: string } }).body?.detail
        : null;
      setErrorMsg(detail || String(err));
      setState("error");
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="border-purple-200 dark:border-purple-800">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles size={16} className="text-purple-500" />
            AI Executive Narrative
            {state !== "idle" && (
              <span className="text-xs font-normal text-muted-foreground ml-1">
                — {effectivePeriod}
              </span>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {state === "done" && (
              <>
                <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={copy}>
                  {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
                  {copied ? "Copied" : "Copy"}
                </Button>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setCollapsed(!collapsed)}>
                  {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                </Button>
              </>
            )}
            <Button
              size="sm"
              variant="outline"
              className={`h-8 gap-1.5 text-xs ${state === "idle" || state === "error" ? "text-purple-600 border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950" : ""}`}
              onClick={generate}
              disabled={!period || state === "loading"}
              title={!period ? "Select a specific period first" : undefined}
            >
              {state === "loading" ? (
                <>
                  <span className="inline-block w-3 h-3 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <Sparkles size={13} />
                  {state === "done" ? "Regenerate" : "Generate Narrative"}
                </>
              )}
            </Button>
          </div>
        </div>
        {!period && (
          <p className="text-xs text-muted-foreground mt-1">Select a specific period to generate a narrative.</p>
        )}
        {state === "error" && (
          <p className="text-xs text-red-500 mt-1">{errorMsg}</p>
        )}
      </CardHeader>

      {state === "loading" && (
        <CardContent className="pt-0">
          <div className="rounded-md bg-muted/40 p-4 flex items-center gap-3 text-muted-foreground text-sm">
            <span className="inline-block w-4 h-4 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
            Analysing submissions and generating narrative…
          </div>
        </CardContent>
      )}

      {state === "done" && narrative && !collapsed && (
        <CardContent className="pt-0">
          <div className="rounded-md bg-muted/40 p-4 text-foreground">
            {renderMarkdown(narrative)}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
