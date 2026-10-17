import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { api, errorNode } from "@/lib/api";
import { highlightSent } from "@/lib/marks";
import { act, destLower, destName, label, plural, purposeName, skipWhy } from "@/lib/text";
import type { Analysis, LogCheck, PersonReport, PersonRow } from "@/lib/types";
import { useApp } from "./ctx";
import * as I from "./icons";
import { InfItem } from "./Turn";

// a native modal: opened and closed from state; Escape, the close button and a click outside all close it
export function Dialog({ id, open, onClose, narrow, title, titleId, intro, headClass, bar, bodyId, live, children }: {
  id: string; open: boolean; onClose: () => void; narrow?: boolean; title: ReactNode; titleId: string; intro: ReactNode;
  headClass?: string; bar?: ReactNode; bodyId?: string; live?: boolean; children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current!;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog id={id} className={narrow ? "narrow" : undefined} aria-labelledby={titleId} ref={ref} onClose={onClose}
      onClick={(e) => { if (e.target === e.currentTarget) ref.current!.close(); }}>
      <div className={`dlg-h${headClass ? ` ${headClass}` : ""}`}>
        <div><h2 id={titleId}>{title}</h2><p>{intro}</p></div>
        <form method="dialog"><button className="icon-btn" aria-label="Close"><I.Close /></button></form>
        {bar}
      </div>
      <div className="dlg-b" id={bodyId} aria-live={live ? "polite" : undefined}>{children}</div>
    </dialog>
  );
}

export type CompareState = { status: "idle" | "loading" | "error"; runs: Analysis[]; error?: ReactNode };

export function CompareDialog({ open, onClose, state }: { open: boolean; onClose: () => void; state: CompareState }) {
  const { meta } = useApp();
  let grid: ReactNode;
  if (state.status === "loading") {
    grid = [0, 1, 2].map((n) => <div key={n} className="cmp-col"><div className="shimmer" /><div className="shimmer" style={{ height: 90 }} /></div>);
  } else if (state.status === "error") {
    grid = <p className="empty">{state.error}</p>;
  } else {
    const actions: Record<string, Set<string>> = {};
    for (const r of state.runs) for (const s of r.spans) (actions[`${s.label}|${s.text}`] ||= new Set()).add(r.blocked ? "block" : act(s, false));
    const diff = new Set(Object.keys(actions).filter((k) => actions[k].size > 1 || state.runs.some((r) => !r.spans.some((s) => `${s.label}|${s.text}` === k))));
    grid = state.runs.map((r, n) => {
      const f = r.flow, a = r.attack;
      const caught = a && a.ran ? a.rounds[0].inferences.filter((i) => i.forbidden && !i.disclosed) : [];
      const atk = !a || !a.ran ? <p className="note-s">{skipWhy(a, r)}</p>
        : caught.length ? <ul className="inf">{caught.map((i, k) => <InfItem key={k} inf={i} then={a.unresolved.length ? "Could not be cleared." : "Made vaguer before sending."} />)}</ul>
        : <p className="note-s">No inference found that this flow forbids.</p>;
      return (
        <div key={n} className="cmp-col">
          <h3>{f.role} to {destLower(f.destination)}<small>for {purposeName(meta, f.purpose)}</small></h3>
          {r.blocked ? <span className="pill stop"><I.Stop /> Blocked</span> : <span className="pill ok"><I.Ok /> Would be sent</span>}
          <div><h4>What would leave</h4>{r.blocked ? <p className="note-s">{r.block_reason ? r.block_reason.why : ""}</p> : <div className="payload">{highlightSent(r, diff)}</div>}</div>
          <div><h4>What an attacker could infer</h4>{atk}</div>
        </div>
      );
    });
  }
  return (
    <Dialog id="compare-dlg" open={open} onClose={onClose} title="Same message, three flows" titleId="cmp-title"
      intro="Dry runs: nothing is sent to any AI. A dashed outline marks an item that another flow handles differently.">
      <div className="cmp-grid" id="cmp-grid">{grid}</div>
    </Dialog>
  );
}

export function sealText(log: LogCheck): ReactNode {
  if (!log.ok) return `The audit log seal is broken at line ${log.broken_at}. ${log.reason}`;
  const old = log.legacy ? ` ${log.legacy} older lines were written before sealing and cannot be checked.` : "";
  return log.chained ? <>Seal intact over {plural(log.chained, "line", "lines")}. Head <code>{log.head}</code>: keep a copy, so lines cut from the end show up.{old}</>
    : `No sealed lines yet.${old}`;
}

function personItem(it: PersonRow["items"][number], row: PersonRow): ReactNode {
  if (!row.sent) return row.blocked ? "not sent, the request was stopped" : "not sent";
  if (it.action === "block") return it.rule === "purpose-minimisation" ? "left out, the purpose did not need it" : "withheld";
  if (it.action === "pseudonymize") return <>sent as placeholder <code>{it.placeholder}</code></>;
  return it.action === "generalize" ? "sent in a vaguer form" : "sent as typed";
}

export function PersonDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { meta } = useApp();
  const [q, setQ] = useState("");
  const [out, setOut] = useState<PersonReport | null>(null);
  const [error, setError] = useState<ReactNode>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);

  const find = async (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    const value = q.trim();
    if (value.length < 2) return;
    setBusy(true);
    try { setOut(await api<PersonReport>("POST", "/api/person-report", { value })); setError(null); }
    catch (err) { setOut(null); setError(errorNode(err)); }
    setBusy(false);
  };

  let rows: ReactNode = null;
  if (error) rows = <p className="empty" style={{ marginTop: 16 }}>{error}</p>;
  else if (out) {
    const seal = <p className="seal">{out.log.ok ? null : <><b>This report may be incomplete.</b> </>}{sealText(out.log)}</p>;
    rows = !out.rows.length ? <><p className="empty" style={{ marginTop: 16 }}>No logged request carried this value. Type a name in full, as the message wrote it.</p>{seal}</>
      : <><div style={{ marginTop: 12 }}>{out.rows.map((r, n) => {
        const f = r.flow, to = r.recipient ? `${r.recipient.model}${r.recipient.simulated ? ", on this laptop" : ` at ${r.recipient.host}`}`
          : r.sent ? `${destName(f.destination)} (model not recorded in older lines)` : "nobody, not sent";
        return (
          <div key={n} className="prow"><span className="when">{new Date(r.ts).toLocaleString("en-IN")}</span>
            <span>{f.role} to {destLower(f.destination)}, {purposeName(meta, f.purpose)}<br /><span className="note-s">Received by {to}</span></span>
            <span>{r.items.map((it, k) => <Fragment key={k}>{k > 0 && <br />}{label(it.label)}: {personItem(it, r)}</Fragment>)}</span></div>
        );
      })}</div>{seal}</>;
  }
  return (
    <Dialog id="person-dlg" narrow open={open} onClose={onClose} titleId="person-title"
      title={out ? `Person report: ${plural(out.matches, "request", "requests")}` : "Person report"}
      intro="Every logged request that carried this person's name or ID: when, where it went, and what happened to it. Matched by keyed hash; what you type is not stored.">
      <form className="person-form" id="person-form" onSubmit={find}>
        <input id="person-q" ref={input} type="text" minLength={2} maxLength={200} required autoComplete="off" placeholder="Full name, Aadhaar, phone…"
          aria-label="Name or ID of the person" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-primary" id="person-go" type="submit" disabled={busy}>Find</button>
      </form>
      <div id="person-rows">{rows}</div>
    </Dialog>
  );
}
