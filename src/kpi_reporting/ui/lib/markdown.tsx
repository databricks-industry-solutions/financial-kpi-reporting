/**
 * Minimal, safe markdown → JSX for model output (Genie answers, AI narratives).
 * Handles headings (#, ##, ###), bullet lists (- or *) and inline **bold**.
 * Everything else renders as plain text; no HTML is injected.
 */
import type { ReactNode } from "react";

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  // With a capture group, split() keeps the bold spans at the odd indexes.
  return text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
    i % 2 === 1 ? (
      <strong key={`${keyPrefix}-${i}`} className="font-semibold">
        {part}
      </strong>
    ) : (
      part
    ),
  );
}

export function renderMarkdown(text: string): ReactNode[] {
  return text.split("\n").map((line, i) => {
    const heading = /^#{1,3}\s+(.*)$/.exec(line);
    if (heading) {
      return (
        <h3 key={i} className="font-semibold text-sm mt-4 mb-1 text-foreground">
          {renderInline(heading[1], `h${i}`)}
        </h3>
      );
    }
    const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
    if (bullet) {
      return (
        <li key={i} className="ml-4 text-sm leading-relaxed list-disc">
          {renderInline(bullet[1], `li${i}`)}
        </li>
      );
    }
    if (line.trim() === "") {
      return <div key={i} className="h-1" />;
    }
    return (
      <p key={i} className="text-sm leading-relaxed">
        {renderInline(line, `p${i}`)}
      </p>
    );
  });
}
