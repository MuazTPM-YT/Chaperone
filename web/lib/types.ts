// shapes of what the gateway's /api/* endpoints return; field names follow the Python side

export type Flow = { role: string; destination: string; purpose: string; pack: string };

export type Decision = { action: string; rule: string; why: string; scope: string; coarse: string };

export type Span = Decision & {
  start: number; end: number; text: string; label: string; subject: string; source: string; score: number;
  note: string; alias: string; replacement: string; covered: boolean;
};

export type Inference = {
  category: string; guess: string; confidence: number; evidence: string[]; description: string; safer: string;
  forbidden: boolean; disclosed: boolean; rule: string;
};

export type Round = { index: number; ms: number; inferences: Inference[]; tightened: string[] };

export type Attack = { ran: boolean; skipped: string; max_rounds: number; rounds: Round[]; unresolved: Inference[] };

export type Mark = { start: number; end: number; placeholder: string; seen: string };
export type Flag = { start: number; end: number; text: string; kind: string; reason: string };
export type Exposure = { turn: number; category: string; guess: string; status: string };

// /api/compare and /api/policies/preview runs: analyze only
export type Analysis = {
  original: string; flow: Flow; outbound: string | null; blocked: boolean; block_reason: Decision | null;
  context_ok: boolean; context_error: string; spans: Span[]; attack: Attack;
  overrides: { label: string; text: string; reason: string }[]; timings: Record<string, number>;
};

// /api/chat: analyze, then send, restore, verify
export type Result = Analysis & {
  reply: string | null; restored: string | null; restore_stats: { exact: number; fuzzy: number } | null;
  restore_marks: Mark[]; flags: Flag[]; error: string | null; sent: boolean; exposure: Exposure[];
};

export type Baseline = { outbound: string | null; inferences: Inference[]; context_ok: boolean; ms: number };

export type Scenario = {
  id: string; group: string; title: string; role: string; destination: string; purpose: string; pack?: string;
  text: string; compare?: { role: string; destination: string; purpose: string }[];
};

export type Endpoint = { model: string; host: string; simulated: boolean };

export type Meta = {
  roles: string[]; destinations: string[]; purposes: string[]; purpose_labels: Record<string, string>;
  scenarios: Scenario[]; dev: boolean; max_text: number;
  packs: { id: string; name: string; short: string; description: string }[];
  admin: boolean; policy_error: string; context_model: string; endpoints: Record<string, Endpoint>;
};

// one pipeline step from /api/chat/stream
export type StepEvent =
  | { step: "detect"; items: { label: string; text: string; source: string }[]; context_ok: boolean; ms: number }
  | { step: "decide"; counts: Record<string, number>; blocked: boolean; ms: number }
  | { step: "attack"; round: number | null; ms: number; found: string[]; skipped: string }
  | { step: "ready"; outbound: string | null; blocked: boolean; ms: number }
  | { step: "guard"; checked: number }
  | { step: "reply"; reply: string; ms: number }
  | { step: "restore"; restored: string; stats: { exact: number; fuzzy: number }; flags: number }
  | { step: "result"; result: Result }
  | { step: "error"; error: string };

export type Rule = {
  id: string; when?: Record<string, string | string[]>; action: string; scope?: string; coarse?: string; why: string;
};

export type Purpose = { id: string; label: string; task: string; omit: string[] };

export type PolicyView = {
  packs: { id: string; name: string; short: string; description: string; extends: string; edited: boolean; rules: Rule[] }[];
  purposes: Purpose[]; edited_purposes: boolean; error: string; admin: boolean;
  vocabulary: Record<string, string[]>;
};

export type LogCheck = {
  ok: boolean; lines: number; chained: number; legacy: number; broken_at: number | null; reason: string; head: string;
};

export type PersonRow = {
  ts: string; conversation: string; flow: Flow; sent: boolean; blocked: boolean; recipient: Endpoint | null;
  items: { label: string; action: string; rule: string; placeholder: string | null }[];
};

export type PersonReport = { matches: number; rows: PersonRow[]; log: LogCheck };
