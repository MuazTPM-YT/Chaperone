import type { Analysis, Attack, Meta, Span } from "./types";

export const SEV: Record<string, number> = { pass: 0, pseudonymize: 1, generalize: 2, block: 3 };
export const ACTION: Record<string, string> = { pass: "Allowed", pseudonymize: "Masked", generalize: "Made vague", block: "Blocked", omit: "Left out" };
export const LABEL: Record<string, string> = { PERSON: "Name", ORG: "Organisation", LOCATION: "Place", AADHAAR: "Aadhaar", PAN: "PAN", GSTIN: "GSTIN",
  IFSC: "IFSC", UPI: "UPI ID", PHONE: "Phone", EMAIL: "Email", VEHICLE: "Vehicle no.", AGE: "Age", DATE: "Date",
  HEALTH: "Health", COMPENSATION: "Pay", MNPI: "Unpublished results", HR: "HR matter", LEGAL: "Legal matter",
  IDENTITY: "Who it is", MRN: "Record no.", ACCOUNT: "Account no.", URL: "Link", IP: "IP address" };
export const CAT: Record<string, string> = { IDENTITY: "Identity", HEALTH: "Health", COMPENSATION: "Pay", HR: "HR", LEGAL: "Legal" };
export const SOURCE: Record<string, string> = { regex: "pattern", ner: "name model", context: "local AI", attacker: "the local attacker" };
export const SKIPPED: Record<string, string> = { "turned off": "Local AI checks are turned off.", "local AI unavailable": "The local AI is not available, so no attack ran.",
  "request already blocked": "Not needed: a rule already stopped the request.", "this flow allows every category": "Not needed: this flow allows every category the attacker looks for." };

export function secs(ms: number): string { return ms < 1 ? "<1 ms" : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`; }
export function label(l: string): string { return LABEL[l] || l; }
export function cap(s: string): string { return s.charAt(0).toUpperCase() + s.slice(1); }
export function plural(n: number, one: string, many: string): string { return `${n} ${n === 1 ? one : many}`; }
export function listJoin(xs: string[]): string { return xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`; }
export function destName(d: string): string { return d === "external" ? "External AI" : "Internal model"; }
export function destLower(d: string): string { return d === "external" ? "external AI" : "internal model"; }
export function maxText(meta: Meta | null): number { return (meta && meta.max_text) || 4000; }

// purpose and rule pack names come from the rule files; in a sentence, lower-case unless it starts with an acronym
export function purposeName(meta: Meta | null, p: string): string {
  const l = (meta && meta.purpose_labels && meta.purpose_labels[p]) || p.replace(/_/g, " ");
  return /^[A-Z]{2}/.test(l) ? l : l.charAt(0).toLowerCase() + l.slice(1);
}
export function packShort(meta: Meta | null, id: string): string { const k = meta && meta.packs.find((x) => x.id === id); return k ? k.short : id; }
export function packNote(meta: Meta | null, id?: string): string { return id && id !== "default" ? `, ${packShort(meta, id)}` : ""; }

// the server counts code points, JS strings count UTF-16 units: without this, every highlight after an emoji shifts
function toUtf16(text: string, items: { start: number; end: number }[] | undefined): void {
  const at = [0];
  for (const ch of text) at.push(at[at.length - 1] + ch.length);
  for (const s of items || []) { s.start = at[s.start] ?? s.start; s.end = at[s.end] ?? s.end; }
}
export function prepare<T extends Analysis & { restored?: string | null; restore_marks?: { start: number; end: number }[]; flags?: { start: number; end: number }[] }>(r: T): T {
  toUtf16(r.original, r.spans);
  if (r.restored) { toUtf16(r.restored, r.restore_marks); toUtf16(r.restored, r.flags); }
  return r;
}

// "local AI unavailable" also covers checks the user turned off; say which
export function skipWhy(a: Attack | undefined, r: Analysis): string {
  return r.context_error === "disabled" ? SKIPPED["turned off"] : SKIPPED[a?.skipped || ""] || "No attack ran.";
}

// purpose minimisation decisions read as their own action
export function act(s: Span, blocked: boolean): string { return blocked ? "block" : s.rule === "purpose-minimisation" ? "omit" : s.action; }

// strictest, widest span wins an overlap: same rule as the server
export function visible(spans: Span[]): Span[] {
  const order = [...spans].sort((a, b) => (Number(a.covered) - Number(b.covered)) || (SEV[b.action] - SEV[a.action]) || ((b.end - b.start) - (a.end - a.start)));
  const out: Span[] = [];
  for (const s of order) if (!out.some((o) => s.start < o.end && o.start < s.end)) out.push(s);
  return out.sort((a, b) => a.start - b.start);
}

// our own token shapes: [PERSON_1], [AGE_1: in their 50s], [PHONE omitted], [PAY withheld]
export const TOKEN = /\[[A-Z]+(?:_\d+(?::[^\]\n]*)?| withheld| omitted)\]/g;
export function tokenKind(t: string): string { return t.endsWith(" omitted]") ? "omit" : t.endsWith(" withheld]") ? "block" : t.includes(":") ? "generalize" : "pseudonymize"; }

export function countsText(c: Record<string, number>): string {
  const parts = [["pseudonymize", "masked"], ["generalize", "made vague"], ["omit", "left out"], ["block", "blocked"], ["pass", "allowed"]]
    .filter(([k]) => c[k]).map(([k, w]) => `${c[k]} ${w}`);
  return parts.length ? cap(listJoin(parts)) + "." : "Nothing to change.";
}

export function newId(): string { return Math.random().toString(36).slice(2); }
