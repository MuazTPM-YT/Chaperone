import type { ReactNode } from "react";
import type { StepEvent } from "./types";

// our own error text, which may carry markup; anything else is shown as plain text
export class GatewayError extends Error {
  node: ReactNode;
  constructor(node: ReactNode, text: string) { super(text); this.node = node; }
}

export function errorNode(e: unknown): ReactNode {
  return e instanceof GatewayError ? e.node : String(e instanceof Error ? e.message : e);
}

const START = "uv run --frozen python -m chaperone";
const unreachable = () => new GatewayError(
  <>Could not reach the gateway. Start it with <code>{START}</code>, then try again.</>, "Could not reach the gateway.");
const plain = (text: string) => new GatewayError(text, text);

export async function post(url: string, body: unknown, maxText: number): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw unreachable();
  }
  if (res.status === 422) throw plain(`The gateway refused this message. It must be 1 to ${maxText.toLocaleString("en-IN")} characters.`);
  if (!res.ok) throw plain(`The gateway answered with error ${res.status}. Its terminal shows the details.`);
  return res;
}

// one JSON object per line, as each pipeline step finishes
export async function stream(url: string, body: unknown, maxText: number, onEvent: (e: StepEvent) => void): Promise<void> {
  const res = await post(url, body, maxText);
  const reader = res.body!.getReader(), dec = new TextDecoder();
  let buf = "", ended = false;
  const take = (line: string) => {
    if (!line.trim()) return;
    const ev = JSON.parse(line) as StepEvent;
    if (ev.step === "result" || ev.step === "error") ended = true;
    onEvent(ev);
  };
  for (;;) {
    let chunk;
    try { chunk = await reader.read(); } catch { throw plain("The connection to the gateway closed before the checks finished."); }
    if (chunk.done) break;
    buf += dec.decode(chunk.value, { stream: true });
    let n;
    while ((n = buf.indexOf("\n")) >= 0) { take(buf.slice(0, n)); buf = buf.slice(n + 1); }
  }
  take(buf);
  if (!ended) throw plain("The gateway stopped before the checks finished. Its terminal shows the details.");
}

// JSON in, JSON out; the server's own error detail is shown when it gives one
export async function api<T>(method: string, url: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw unreachable();
  }
  if (res.ok) return res.json();
  let detail: unknown = "";
  try { detail = (await res.json()).detail; } catch { /* not JSON */ }
  throw plain(typeof detail === "string" && detail ? detail : `The gateway answered with error ${res.status}. Its terminal shows the details.`);
}
