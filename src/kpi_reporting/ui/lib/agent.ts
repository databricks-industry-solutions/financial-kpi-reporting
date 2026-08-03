/**
 * Agent streaming helpers — separate from the generated api.ts so they
 * survive `apx build` regenerating the API client.
 */

/**
 * Streams an SSE endpoint and calls onToken for each token, onDone when complete.
 * Pass an AbortController signal to cancel mid-stream.
 */
export async function streamAgent(
  url: string,
  body: unknown,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
  signal?: AbortSignal,
) {
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    onError(String(err));
    return;
  }

  if (!res.ok) {
    const text = await res.text();
    let msg = `${res.status}: ${text}`;
    try {
      const parsed = JSON.parse(text);
      if (parsed?.detail) msg = parsed.detail;
    } catch { /* keep raw text */ }
    onError(msg);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) { onError("No response body"); return; }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (!payload) continue;
        try {
          const evt = JSON.parse(payload) as Record<string, unknown>;
          if (evt.done) { onDone(); return; }
          if (evt.error) { onError(String(evt.error)); return; }
          if (typeof evt.token === "string") onToken(evt.token);
        } catch { /* ignore parse errors */ }
      }
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") onError(String(err));
    return;
  }
  onDone();
}
