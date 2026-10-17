import { Fragment, useEffect, useRef, useState, type SubmitEvent, type ReactNode } from "react";
import { highlightOriginal, highlightSent, rawReply, restoredReply, tokenMarks } from "@/lib/marks";
import { ACTION, CAT, SKIPPED, SOURCE, act, cap, countsText, destLower, destName, label, listJoin, packNote, plural, purposeName, secs, skipWhy, visible } from "@/lib/text";
import type { Turn } from "@/lib/turn";
import type { Baseline, Inference, Result } from "@/lib/types";
import { RuleRef, useApp } from "./ctx";
import * as I from "./icons";

export type TurnActions = {
  busy: boolean;
  onToggle: (t: Turn, key: string, open: boolean) => void;
  onInclude: (t: Turn, item: { label: string; text: string }, reason: string) => void;
  onCopy: (t: Turn) => Promise<boolean>;
};

type State = "done" | "fail" | "warn" | "active" | "skip" | "pending";

function Step({ state, title, summary, ms, children }: { state: State; title: string; summary?: ReactNode; ms?: number | null; children?: ReactNode }) {
  const node = state === "done" ? <I.Ok /> : state === "fail" ? <I.Stop /> : state === "warn" ? <I.Alert /> : state === "active" ? <I.Dot /> : null;
  return (
    <li className={`step ${state}`}>
      <span className="node">{node}</span>
      <div className="step-b">
        <div className="step-h"><b>{title}</b>{ms != null && <span className="ms">{secs(ms)}</span>}</div>
        {summary ? <p className="step-s">{summary}</p> : null}
        {children}
      </div>
    </li>
  );
}

function Details({ t, k, a, children }: { t: Turn; k: string; a: TurnActions; children: ReactNode }) {
  return (
    <details className="more" open={t.open.has(k)} onToggle={(e) => a.onToggle(t, k, (e.currentTarget as HTMLDetailsElement).open)}>
      <summary><I.Chev />Details</summary>
      <div className="detail">{children}</div>
    </details>
  );
}

export function InfItem({ inf, then }: { inf: Inference; then?: string }) {
  return (
    <li className={inf.forbidden ? "" : "muted"}>
      <div className="top"><span className="chip cat">{CAT[inf.category] || inf.category}</span>
        <span className="guess">{inf.guess}</span><span className="conf">{Math.round(inf.confidence * 100)}% sure</span></div>
      <div className="ev">from {inf.evidence.map((e, i) => <code key={i}>{e}</code>)}</div>
      {then ? <div className="then">{then}</div> : null}
    </li>
  );
}

function Decisions({ r, t, a }: { r: Result; t: Turn; a: TurnActions }) {
  const [asking, setAsking] = useState<Set<number>>(new Set());
  if (!r.spans.length) return <p className="empty">Nothing sensitive found.</p>;
  const rows: { key: string; s: Result["spans"][number]; n: number }[] = [];
  for (const s of [...r.spans].sort((x, y) => x.start - y.start)) {
    const key = [s.text, s.label, s.action, s.rule, s.covered].join("\u0001");
    const seen = rows.find((x) => x.key === key);
    if (seen) seen.n += 1; else rows.push({ key, s, n: 1 });
  }
  const submit = (e: SubmitEvent<HTMLFormElement>, s: Result["spans"][number]) => {
    e.preventDefault();
    const reason = (e.currentTarget.elements[0] as HTMLInputElement).value.trim();
    if (reason.length < 8 || a.busy) return;
    a.onInclude(t, { label: s.label, text: s.text }, reason);
  };
  return (
    <ul className="dl">{rows.map(({ s, n }, i) => {
      const k = act(s, r.blocked);
      const becomes = r.blocked ? "not sent" : s.covered ? "inside a wider item" : s.action === "pass" ? "as typed" : s.replacement || "";
      const note = s.note && s.note !== "local LLM" ? ` (${s.note})` : "";
      const who = s.subject === "unknown" ? "" : `${s.subject === "business" ? "business data" : "personal data"}, `;
      const canInclude = k === "omit" && !r.blocked;
      return (
        <li key={i} className={s.covered ? "covered" : ""}>
          <div className="top"><span className={`chip ${k}`}>{ACTION[k]}</span><span className="chip plain">{label(s.label)}</span>{n > 1 ? <span className="note-s">×{n}</span> : null}</div>
          <span className="val">{s.text}</span><span className="as">sent as {becomes}</span>
          <span className="why">{cap(`${who}found by ${SOURCE[s.source] || s.source}`)}{note}. Rule <RuleRef id={s.rule} pack={r.flow.pack} />: {s.why}</span>
          {canInclude && <>
            {asking.has(i) ? <form className="include-form" onSubmit={(e) => submit(e, s)}>
              <input type="text" minLength={8} maxLength={200} required placeholder="Why does this purpose need it?" aria-label="Reason (logged, names removed)" autoFocus />
              <button className="btn btn-quiet" type="submit">Include and send again</button>
            </form> : <button type="button" className="chip-btn" onClick={() => setAsking(new Set(asking).add(i))}>Include anyway</button>}
          </>}
        </li>
      );
    })}</ul>
  );
}

function BaselineBlock({ r, base }: { r: Result; base: Turn["baseline"] }) {
  if (r.flow.destination !== "external" || !r.attack || !r.attack.ran) return null;
  const head = <h4>If only names and IDs were masked</h4>;
  if (base === undefined || base === "loading") return <div>{head}<div className="shimmer" aria-label="Loading comparison" /></div>;
  if (base === null) return null;
  const infs = base.inferences.filter((i) => i.forbidden);
  if (!infs.length) return <div>{head}<p className="note-s">The local attacker found nothing there either.</p></div>;
  return <div>{head}<ul className="inf">{infs.map((i, n) => <InfItem key={n} inf={i} />)}</ul>
    <p className="note-s" style={{ marginTop: 6 }}>Our own names-and-IDs-only setting, the way type-based masking tools work. Not any specific product.</p></div>;
}

function AttackDetail({ r, base }: { r: Result; base: Turn["baseline"] }) {
  const a = r.attack;
  if (!a || !a.ran) return <><p className="note-s">{skipWhy(a, r)}</p><BaselineBlock r={r} base={base} /></>;
  const rounds = a.rounds, first = rounds[0].inferences, last = rounds[rounds.length - 1].inferences;
  const caught = first.filter((i) => i.forbidden && !i.disclosed);
  const allowed = last.filter((i) => !i.forbidden);
  const disclosed = rounds.flatMap((x) => x.inferences).filter((i) => i.disclosed);
  const tightened = rounds.flatMap((x) => x.tightened);
  const none = !a.unresolved.length && !caught.length && !disclosed.length && !allowed.length;
  return <>
    {a.unresolved.length > 0 && <div><h4>Still inferable</h4><ul className="inf">{a.unresolved.map((i, n) => <InfItem key={n} inf={i} />)}</ul></div>}
    {caught.length > 0 && <div><h4>Before tightening</h4><ul className="inf">{caught.map((i, n) =>
      <InfItem key={n} inf={i} then={a.unresolved.length ? "" : "Those words were made vaguer before sending."} />)}</ul>
      {tightened.length > 0 && <p className="note-s" style={{ marginTop: 6 }}>Words changed: {tightened.map((x, n) => <Fragment key={n}>{n > 0 && ", "}<code>{x}</code></Fragment>)}.</p>}</div>}
    {disclosed.length > 0 && <div><h4>Already disclosed earlier</h4><ul className="inf">{disclosed.map((i, n) => <InfItem key={n} inf={i} then="Sent in an earlier message; it cannot be pulled back." />)}</ul></div>}
    {allowed.length > 0 && <div><h4>Allowed for this flow</h4><ul className="inf">{allowed.map((i, n) => <InfItem key={n} inf={i} />)}</ul></div>}
    {none && <p className="note-s">The local attacker found nothing this flow forbids.</p>}
    <BaselineBlock r={r} base={base} />
    <p className="note-s">{plural(rounds.length, "attack pass", "attack passes")}. A small local model can miss what a large one would infer, so &quot;nothing found&quot; is weak evidence, never a guarantee.</p>
  </>;
}

// what masking names alone would have leaked, said once, in the attack step itself
function BaselineCallout({ t }: { t: Turn }) {
  const b = t.baseline;
  if (!b || b === "loading" || !t.result || t.result.blocked) return null;
  const leaked = (b as Baseline).inferences.filter((i) => i.forbidden).map((i) => i.guess);
  return leaked.length ? <div className="callout">Masking names and IDs alone would have let a reader infer {listJoin([...new Set(leaked)])}.</div> : null;
}

function RestoreDetail({ r }: { r: Result }) {
  const seen = new Map<string, string>();
  for (const m of r.restore_marks || []) if (!seen.has(m.placeholder)) seen.set(m.placeholder, (r.restored || "").slice(m.start, m.end));
  const flags = r.flags || [];
  return <>
    {seen.size ? <ul className="dl">{[...seen].map(([ph, v]) => <li key={ph}><span className="as">{ph}</span><span className="val">{v}</span></li>)}</ul>
      : <p className="note-s">The reply had no placeholders to put back.</p>}
    {flags.length > 0 && <div className="flags"><b>{plural(flags.length, "detail", "details")} in the reply {flags.length === 1 ? "is" : "are"} not from your message.</b>
      <ul>{flags.map((f, n) => <li key={n}><code>{f.text}</code>: {f.reason}</li>)}</ul></div>}
  </>;
}

function OutSteps({ t, i, turns, a }: { t: Turn; i: number; turns: Turn[]; a: TurnActions }) {
  const st = t.steps, r = t.result, ended = Boolean(r || t.error);
  const out: ReactNode[] = [];
  // 1. find
  if (st.detect) {
    const items: typeof st.detect.items = [], keys = new Set<string>();
    for (const it of st.detect.items) { const k = `${it.label}|${it.text}`; if (!keys.has(k)) { keys.add(k); items.push(it); } }
    // one chip per kind and outcome, with a count: "Health ×3", not three chips
    const kinds = new Map<string, { k: string; l: string; n: number }>();
    // words the attacker flagged later belong to the attack step, not to what was found here
    const own = r ? visible(r.spans.filter((s) => s.source !== "attacker")).filter((s) => !s.covered) : null;
    for (const [k, l] of own ? own.map((s) => [act(s, r!.blocked), s.label]) : items.map((it) => ["plain", it.label])) {
      const key = `${k}|${l}`;
      kinds.set(key, { k, l, n: (kinds.get(key)?.n || 0) + 1 });
    }
    // the full warning once per chat; later turns get the short form
    const said = turns.slice(0, i).some((x) => x.steps.detect && !x.steps.detect.context_ok);
    const off = t.flow.use_context ? "offline" : "turned off";
    const warn = st.detect.context_ok ? null : t.flow.destination === "external" ? <div className="callout">Local checks are {off}, so nothing goes to an external AI.</div>
      : said ? <div className="callout">Local AI checks {off}: only IDs and names checked.</div>
      : <div className="callout">Local AI checks are {off}. Only IDs and names were checked; health, pay, HR, legal details and inferences can go through unnoticed.</div>;
    out.push(<Step key="find" state={st.detect.context_ok ? "done" : "warn"} title="Find what is sensitive"
      summary={items.length ? `${plural(items.length, "item", "items")} found.` : "Nothing sensitive found."} ms={st.detect.ms}>
      {kinds.size > 0 && <div className="found">{[...kinds.values()].map(({ k, l, n }) =>
        <span key={`${k}|${l}`} className={`chip ${k}`} title={ACTION[k]}>{label(l)}{n > 1 ? ` ×${n}` : ""}</span>)}</div>}
      {warn}
    </Step>);
  } else out.push(<Step key="find" state={ended ? "fail" : "active"} title="Find what is sensitive" summary={ended ? "Did not finish." : "Reading for names, IDs, health, pay and more…"} />);
  // 2. rules
  if (st.decide) {
    out.push(<Step key="rules" state={st.decide.blocked ? "fail" : "done"} title="Apply the rules for this flow"
      summary={st.decide.blocked ? "A rule stops the whole request." : countsText(st.decide.counts)} ms={st.decide.ms}>
      {r && r.overrides.length > 0 && <div className="callout info">Included anyway: {listJoin(r.overrides.map((o) => label(o.label)))}. Your reason is in the audit log, with names removed.</div>}
      {r && <Details t={t} k="decide" a={a}><Decisions r={r} t={t} a={a} /></Details>}
    </Step>);
  } else out.push(<Step key="rules" state={st.detect && !ended ? "active" : "pending"} title="Apply the rules for this flow" summary="Deciding what may leave…" />);
  // 3. attack
  const rounds = st.attack.filter((x) => x.round !== null), skip = st.attack.find((x) => x.round === null);
  const atkMs = rounds.reduce((s, x) => s + x.ms, 0);
  const title = "Try to work out who and what";
  if (skip) {
    const why = t.flow.use_context ? SKIPPED[skip.skipped] || skip.skipped : SKIPPED["turned off"];
    out.push(<Step key="attack" state="skip" title={title} summary={why} ms={null}>{r && <BaselineCallout t={t} />}</Step>);
  } else if (st.ready || (r && rounds.length)) {
    const caught = rounds.some((x) => x.found.length), unresolved = r && r.attack.unresolved.length;
    const first = rounds.find((x) => x.found.length);
    const summary = unresolved ? `Could still infer ${listJoin(r!.attack.unresolved.map((x) => x.guess))} after ${plural(r!.attack.max_rounds, "round", "rounds")} of tightening.`
      : caught ? `Inferred ${listJoin(first!.found)}. Those words were made vaguer, then the attacker found nothing this flow forbids.`
      : "No inference found that this flow forbids.";
    out.push(<Step key="attack" state={unresolved ? "fail" : caught ? "warn" : "done"} title={title} summary={summary} ms={atkMs}>
      <BaselineCallout t={t} />
      {r && <Details t={t} k="attack" a={a}><AttackDetail r={r} base={t.baseline} /></Details>}
    </Step>);
  } else if (st.decide && !ended) {
    const last = rounds[rounds.length - 1];
    const live = !last ? "A local attacker reads the protected version…"
      : last.found.length ? `Round ${last.round! + 1}: inferred ${listJoin(last.found)}. Making those words vaguer, then reading again…` : "Reading again…";
    out.push(<Step key="attack" state="active" title={title} summary={live} ms={rounds.length ? atkMs : null} />);
  } else out.push(<Step key="attack" state="pending" title={title} summary="" />);
  // 4. final check
  const blocked = (st.ready && st.ready.blocked) || (r && r.blocked);
  const fc = "Final check";
  if (blocked) out.push(<Step key="final" state="skip" title={fc} summary="Nothing to send." />);
  else if (st.guard) out.push(<Step key="final" state="done" title={fc} summary={`No masked value is left in what goes out. Sent to ${destLower(t.flow.destination)}.`} />);
  else if (st.ready && !ended) out.push(<Step key="final" state="active" title={fc} summary="Checking the payload for every masked value…" />);
  else if (ended && st.ready) out.push(<Step key="final" state="fail" title={fc} summary={r && r.error ? r.error : "Did not finish."} />);
  else out.push(<Step key="final" state="pending" title={fc} summary="" />);
  return <ol className="steps">{out}</ol>;
}

function Outcome({ t }: { t: Turn }) {
  const r = t.result;
  if (t.error) return <div className="outcome stop"><I.Stop /><span>{t.error}</span></div>;
  if (!r) return null;
  const time = <span className="t">{secs(r.timings.total_ms)}{r.timings.llm_ms ? ` + AI ${secs(r.timings.llm_ms)}` : ""}</span>;
  if (r.blocked) return <>
    <div className="outcome stop"><I.Stop /><span>Blocked. Nothing left this laptop.</span>{time}</div>
    <p className="note-s" style={{ marginTop: 6 }}>Rule <RuleRef id={r.block_reason!.rule} pack={r.flow.pack} />: {r.block_reason!.why}</p>
  </>;
  if (!r.sent && (r.error || "").startsWith("Outbound guard")) return <div className="outcome stop"><I.Stop /><span>Not sent. The final check stopped it.</span>{time}</div>;
  const changed = r.spans.filter((s) => !s.covered && s.action !== "pass").length;
  const what = changed ? `Sent with ${plural(changed, "change", "changes")}.` : "Sent as typed.";
  if (!r.sent) return <div className="outcome note"><I.Alert /><span>{what} The AI did not answer.</span>{time}</div>;
  return <div className="outcome ok"><I.Ok /><span>{what}</span>{time}</div>;
}

function CopyButton({ t, a }: { t: Turn; a: TurnActions }) {
  const [copied, setCopied] = useState(false);
  return <button type="button" className="copy" onClick={async () => {
    if (await a.onCopy(t)) { setCopied(true); setTimeout(() => setCopied(false), 1600); }
  }}>{copied ? "Copied" : "Copy"}</button>;
}

// keep a live turn in view: all of it while it fits, its start once it is taller than the screen, so the steps are never scrolled past
function follow(el: HTMLElement) {
  const s = document.getElementById("stage")!;
  requestAnimationFrame(() => {
    const top = el.offsetTop - (document.querySelector(".lane-heads") as HTMLElement).offsetHeight - 8, end = s.scrollHeight - s.clientHeight;
    s.scrollTo({ top: Math.max(0, Math.min(top, end)), behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });
}

export function TurnView({ t, i, turns, a }: { t: Turn; i: number; turns: Turn[]; a: TurnActions }) {
  const { meta } = useApp();
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (t.follow && ref.current) follow(ref.current);
  });
  const st = t.steps, r = t.result, f = t.flow, to = destName(f.destination);
  let ai: ReactNode;
  if ((st.ready && st.ready.blocked) || (r && r.blocked)) {
    ai = <div className="ghost enter"><b>Nothing was sent.</b> {to} never saw this message.</div>;
  } else if (st.guard) {
    ai = <><span className="cap">{to} received</span><div className="bubble theirs enter-r"><div className="plain">{r ? highlightSent(r) : tokenMarks(st.ready!.outbound || "")}</div></div></>;
  } else if (t.error || (r && !r.sent)) {
    ai = <div className="ghost enter"><b>Not sent.</b> {to} never saw this message.</div>;
  } else ai = <p className="waiting">Waiting for the checks…</p>;

  let back: ReactNode = null;
  if (st.guard) {
    let theirs: ReactNode, mid: ReactNode, mine: ReactNode = null;
    if (st.reply) theirs = <><span className="cap">{to} replied</span><div className="bubble theirs back enter"><div className="md">{rawReply(st.reply.reply)}</div></div></>;
    else if (r && r.error) theirs = <div className="ghost"><b>No reply.</b> {r.error}</div>;
    else theirs = <><span className="cap">{to} is writing</span><div className="typing" aria-label="Writing"><i /><i /><i /></div></>;
    if (st.restore) {
      const flagged = st.restore.flags ? ` ${plural(st.restore.flags, "detail", "details")} in the reply ${st.restore.flags === 1 ? "is" : "are"} not from your message.` : "";
      const n = st.restore.stats.exact + st.restore.stats.fuzzy;
      mid = <Step state={st.restore.flags ? "warn" : "done"} title="Put the real values back"
        summary={(n ? `${plural(n, "placeholder", "placeholders")} replaced with the real value.` : "No placeholders to replace.") + flagged}>
        {r && <Details t={t} k="restore" a={a}><RestoreDetail r={r} /></Details>}
      </Step>;
      mine = <><div className="cap-row">{r && r.restored ? <CopyButton t={t} a={a} /> : null}<span className="cap">You get back</span></div>
        <div className="bubble mine back enter-l"><div className="md">{r ? restoredReply(r) : st.restore.restored}</div></div></>;
    } else if (st.reply) {
      mid = <Step state="active" title="Put the real values back" summary="Swapping placeholders for real values…" />;
    } else {
      mid = <Step state={r && r.error ? "skip" : "pending"} title="Put the real values back" summary={r && r.error ? "Nothing came back to restore." : ""} />;
    }
    back = <div className="row back"><div className="cell you">{mine}</div><div className="mid-col"><ol className="steps">{mid}</ol></div><div className="cell ai">{theirs}</div></div>;
  }

  return (
    <article className="turn" id={`turn-${i}`} aria-label={`Message ${i + 1}`} ref={ref}>
      <div className="row out">
        <div className="cell you"><span className="cap">You wrote</span><div className="bubble mine enter"><div className="plain">{r ? highlightOriginal(r) : t.text}</div></div></div>
        <div className="mid-col">
          <p className="flowline"><b>{f.role}</b> to <b>{destLower(f.destination)}</b>, for {purposeName(meta, f.purpose)}{packNote(meta, f.pack)}</p>
          <OutSteps t={t} i={i} turns={turns} a={a} />
          <Outcome t={t} />
        </div>
        <div className="cell ai">{ai}</div>
      </div>
      {back}
    </article>
  );
}
