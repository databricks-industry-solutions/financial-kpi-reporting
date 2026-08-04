import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Sparkles, Send, Loader2, ChevronDown, ChevronRight, AlertCircle } from "lucide-react";
import { useGenieAsk } from "@/lib/api";
import type { GenieAttachment } from "@/lib/api";

const SAMPLE_QUESTIONS = [
  "What is the average Revenue Growth across all regions for Jan 2026?",
  "Which region has the highest Operating Margin?",
  "Compare DSO across all regions for Dec 2025",
  "Show all planned actions for regions with Cautious sentiment",
  "What external factors are most commonly reported?",
  "Which KPIs mention supply chain in their key drivers?",
  "List internal factors for regions where OPEX Ratio exceeds 23%",
];

const MAX_DISPLAY_ROWS = 50;

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  attachments?: GenieAttachment[];
  error?: boolean;
}

function AttachmentView({ attachment }: { attachment: GenieAttachment }) {
  const [sqlOpen, setSqlOpen] = useState(false);
  const hasData = attachment.columns.length > 0 && attachment.data_array.length > 0;
  const displayRows = attachment.data_array.slice(0, MAX_DISPLAY_ROWS);

  return (
    <div className="space-y-2 mt-2">
      {attachment.sql && (
        <div>
          <button
            type="button"
            onClick={() => setSqlOpen(!sqlOpen)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {sqlOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            SQL Query
          </button>
          {sqlOpen && (
            <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto whitespace-pre-wrap">
              {attachment.sql}
            </pre>
          )}
        </div>
      )}
      {hasData && (
        <div className="border rounded overflow-hidden">
          <div className="overflow-x-auto max-h-80">
            <Table>
              <TableHeader>
                <TableRow>
                  {attachment.columns.map((col) => (
                    <TableHead key={col} className="text-xs whitespace-nowrap">
                      {col}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayRows.map((row, i) => (
                  <TableRow key={i}>
                    {row.map((cell, j) => (
                      <TableCell key={j} className="text-xs py-1 whitespace-nowrap">
                        {cell}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="px-3 py-1.5 bg-muted text-xs text-muted-foreground border-t">
            {attachment.row_count} row{attachment.row_count !== 1 ? "s" : ""}
            {attachment.row_count > MAX_DISPLAY_ROWS && ` (showing first ${MAX_DISPLAY_ROWS})`}
            {attachment.truncated && " — results truncated by Genie"}
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-primary text-primary-foreground"
            : message.error
              ? "bg-destructive/10 text-destructive"
              : "bg-muted"
        }`}
      >
        {message.error && (
          <div className="flex items-center gap-1 mb-1">
            <AlertCircle className="h-3 w-3" />
            <span className="text-xs font-medium">Error</span>
          </div>
        )}
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.attachments?.map((att, i) => (
          <AttachmentView key={i} attachment={att} />
        ))}
      </div>
    </div>
  );
}

export function GenieChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { mutate: askGenie, isPending } = useGenieAsk({
    mutation: {
      onSuccess: (result) => {
        const resp = result.data;
        setConversationId(resp.conversation_id);

        const textParts = resp.attachments
          .map((a) => a.text)
          .filter(Boolean);
        const content = textParts.length > 0
          ? textParts.join("\n\n")
          : resp.status === "COMPLETED" || resp.status === "EXECUTING_QUERY"
            ? "Here are the results:"
            : resp.error
              ? `Genie error: ${resp.error}`
              : `Query ended with status: ${resp.status}`;

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content,
            attachments: resp.attachments.filter(
              (a) => a.sql || (a.columns.length > 0 && a.data_array.length > 0)
            ),
            error: resp.status === "FAILED",
          },
        ]);
      },
      onError: (error) => {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: error.message || "Something went wrong. Please try again.",
            error: true,
          },
        ]);
      },
    },
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isPending]);

  const handleSend = (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || isPending) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    askGenie({ content: question, conversation_id: conversationId });
  };

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          Financial KPI Analyst
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Ask natural language questions about KPI values, justifications, and planned actions. Powered by Databricks Genie.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 pt-0">
        {/* Sample question chips (show when no messages) */}
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-1.5">
            {SAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => handleSend(q)}
                disabled={isPending}
                className="text-xs bg-muted hover:bg-muted/80 rounded-full px-3 py-1.5 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Chat messages */}
        {messages.length > 0 && (
          <ScrollArea className="h-[400px]">
            <div ref={scrollRef} className="space-y-3 pr-3 h-[400px] overflow-y-auto">
              {messages.map((msg, i) => (
                <MessageBubble key={i} message={msg} />
              ))}
              {isPending && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-3 py-2 text-sm flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Analyzing...
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        )}

        {/* Input bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about KPIs..."
            disabled={isPending}
            className="text-sm"
          />
          <Button type="submit" size="icon" disabled={isPending || !input.trim()}>
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
