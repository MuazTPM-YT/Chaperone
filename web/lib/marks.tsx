import { Fragment, type ReactNode } from "react";
import { ACTION, TOKEN, act, label, tokenKind, visible } from "./text";
import type { Analysis, Result } from "./types";

export function highlightOriginal(r: Analysis): ReactNode {
  const out: ReactNode[] = [];
  let pos = 0;
  for (const s of visible(r.spans)) {
    const a = act(s, false);
    out.push(r.original.slice(pos, s.start),
      <mark key={s.start} className={a} title={`${label(s.label)}: ${ACTION[a]}`}>{r.original.slice(s.start, s.end)}<sup>{label(s.label)}</sup></mark>);
    pos = s.end;
  }
  out.push(r.original.slice(pos));
  return out;
}

// rebuild the payload with marks; if it does not match the server byte for byte, show the server's text plain
export function highlightSent(r: Analysis, diff?: Set<string>): ReactNode {
  const out: ReactNode[] = [];
  let plain = "", pos = 0;
  for (const s of visible(r.spans.filter((x) => !x.covered && x.action !== "pass" && x.replacement))) {
    const a = act(s, false), d = diff && diff.has(`${s.label}|${s.text}`) ? " diff" : "";
    out.push(r.original.slice(pos, s.start), <mark key={s.start} className={a + d} title={`${label(s.label)}: ${ACTION[a]}`}>{s.replacement}</mark>);
    plain += r.original.slice(pos, s.start) + s.replacement;
    pos = s.end;
  }
  out.push(r.original.slice(pos));
  plain += r.original.slice(pos);
  return plain === r.outbound ? out : r.outbound;
}

// the outbound text before the final result: marks come from our own token shapes
export function tokenMarks(text: string): ReactNode {
  const out: ReactNode[] = [];
  let pos = 0;
  for (const m of text.matchAll(TOKEN)) {
    out.push(text.slice(pos, m.index), <mark key={m.index} className={tokenKind(m[0])}>{m[0]}</mark>);
    pos = m.index + m[0].length;
  }
  out.push(text.slice(pos));
  return out;
}

type Range = { start: number; end: number; mark: (text: string) => ReactNode };

const SENTINEL = /\u0000(\d+)\u0000/;

// bold, then code, then our marks: the same order the page always used
function inline(s: string, keep: Range[], text: string, key: string): ReactNode[] {
  const marks = (part: string, k: string): ReactNode[] => part.split(SENTINEL).map((x, i) => {
    if (i % 2) { const r = keep[+x]; return <Fragment key={`${k}m${i}`}>{r.mark(text.slice(r.start, r.end))}</Fragment>; }
    return x.split("\n").map((line, j) => <Fragment key={`${k}t${i}.${j}`}>{j > 0 && <br />}{line}</Fragment>);
  });
  const code = (part: string, k: string): ReactNode[] => part.split(/`([^`]+)`/).map((x, i) =>
    i % 2 ? <code key={`${k}c${i}`}>{marks(x, `${k}c${i}`)}</code> : <Fragment key={`${k}c${i}`}>{marks(x, `${k}c${i}`)}</Fragment>);
  return s.split(/\*\*(.+?)\*\*/).map((x, i) =>
    i % 2 ? <strong key={`${key}b${i}`}>{code(x, `${key}b${i}`)}</strong> : <Fragment key={`${key}b${i}`}>{code(x, `${key}b${i}`)}</Fragment>);
}

// tiny markdown: paragraphs, lists, headings, rules, bold, code; marked ranges survive it
export function markedMarkdown(text: string, ranges: Range[]): ReactNode {
  const keep: Range[] = [];
  for (const r of [...ranges].sort((a, b) => a.start - b.start)) if (!keep.some((k) => r.start < k.end && k.start < r.end)) keep.push(r);
  let t = "", pos = 0;
  keep.forEach((r, i) => { t += text.slice(pos, r.start) + `\u0000${i}\u0000`; pos = r.end; });
  t += text.slice(pos);

  const out: ReactNode[] = [];
  let list: { kind: "ul" | "ol"; items: string[] } | null = null, para: string[] = [];
  const flush = () => { if (para.length) { const k = `p${out.length}`; out.push(<p key={k}>{inline(para.join("\n"), keep, text, k)}</p>); para = []; } };
  const close = () => {
    if (!list) return;
    const k = `l${out.length}`, items = list.items.map((x, i) => <li key={i}>{inline(x, keep, text, `${k}.${i}`)}</li>);
    out.push(list.kind === "ul" ? <ul key={k}>{items}</ul> : <ol key={k}>{items}</ol>);
    list = null;
  };
  const item = (kind: "ul" | "ol", x: string) => { if (!list || list.kind !== kind) { close(); list = { kind, items: [] }; } list.items.push(x); };
  for (const raw of t.split("\n")) {
    const line = raw.trimEnd();
    let m;
    if (!line.trim()) { flush(); close(); }
    else if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { flush(); close(); out.push(<hr key={`r${out.length}`} />); }
    else if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) { flush(); close(); const k = `h${out.length}`; out.push(<h4 key={k}>{inline(m[1], keep, text, k)}</h4>); }
    else if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) { flush(); item("ul", m[1]); }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) { flush(); item("ol", m[1]); }
    else { close(); para.push(line); }
  }
  flush(); close();
  return out;
}

// placeholders the way the AI wrote them, before they are put back
export function rawReply(text: string): ReactNode {
  const ranges = [...text.matchAll(TOKEN)].map((m) => ({ start: m.index, end: m.index + m[0].length,
    mark: (x: string) => <mark className={tokenKind(m[0])}>{x}</mark> }));
  return markedMarkdown(text, ranges);
}

export function restoredReply(r: Result): ReactNode {
  const restored = r.restored || "";
  const ranges: Range[] = [
    ...(r.flags || []).map((f) => ({ start: f.start, end: f.end, mark: (x: string) => <mark className="flag" title={f.reason}>{x}</mark> })),
    ...(r.restore_marks || []).map((m) => ({ start: m.start, end: m.end, mark: (x: string) => <mark className="pseudonymize" title={`The AI saw ${m.seen}`}>{x}</mark> })),
    // what never left stays visibly missing in the reply
    ...[...restored.matchAll(/\[[A-Z]+ (?:omitted|withheld)\]/g)].map((m) => ({ start: m.index, end: m.index + m[0].length,
      mark: (x: string) => <mark className={m[0].includes("omitted") ? "omit" : "block"}>{x}</mark> })),
  ];
  return markedMarkdown(restored, ranges);
}
