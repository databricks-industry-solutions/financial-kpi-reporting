/**
 * JustifyButton — appears next to each justification textarea in the edit sheet.
 * On click it streams a drafted justification from the agent endpoint and
 * inserts it into the textarea, which the user can then edit or discard.
 */
import { useRef, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { streamAgent } from "@/lib/agent";

interface JustifyButtonProps {
  submissionId: string;
  field: string;
  onDraft: (text: string) => void;
}

export function JustifyButton({ submissionId, field, onDraft }: JustifyButtonProps) {
  const [state, setState] = useState<"idle" | "streaming" | "done" | "error">("idle");
  const [draft, setDraft] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const start = async () => {
    if (state === "streaming") {
      abortRef.current?.abort();
      setState("idle");
      setDraft("");
      return;
    }

    setState("streaming");
    setDraft("");
    setErrorMsg("");

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    let accumulated = "";

    await streamAgent(
      "/api/agent/justify",
      { submission_id: submissionId, field },
      (token) => {
        accumulated += token;
        setDraft(accumulated);
      },
      () => {
        setState("done");
      },
      (msg) => {
        setErrorMsg(msg);
        setState("error");
      },
      ctrl.signal,
    );
  };

  const accept = () => {
    onDraft(draft);
    setState("idle");
    setDraft("");
  };

  const discard = () => {
    setState("idle");
    setDraft("");
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={start}
          className="h-7 gap-1.5 text-xs text-purple-600 border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950"
          disabled={state === "done"}
        >
          {state === "streaming" ? (
            <>
              <span className="inline-block w-3 h-3 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
              Stop
            </>
          ) : (
            <>
              <Sparkles size={12} />
              AI Draft
            </>
          )}
        </Button>

        {state === "error" && (
          <span className="text-xs text-red-500">{errorMsg}</span>
        )}
      </div>

      {(state === "streaming" || state === "done") && draft && (
        <div className="rounded-md border border-purple-200 bg-purple-50 dark:bg-purple-950/30 dark:border-purple-800 p-2.5 text-sm leading-relaxed text-foreground relative">
          <p className="pr-6 whitespace-pre-wrap">{draft}{state === "streaming" && <span className="animate-pulse">▋</span>}</p>
          {state === "done" && (
            <div className="flex gap-2 mt-2">
              <Button size="sm" variant="default" className="h-7 text-xs gap-1 bg-purple-600 hover:bg-purple-700" onClick={accept}>
                <Sparkles size={11} /> Use this
              </Button>
              <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={discard}>
                <X size={11} /> Discard
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
