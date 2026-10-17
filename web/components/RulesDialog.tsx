import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, errorNode } from "@/lib/api";
import { tokenMarks } from "@/lib/marks";
import { ACTION, act, destLower, destName, label, plural, prepare, purposeName } from "@/lib/text";
import type { Analysis, PolicyView, Purpose, Rule } from "@/lib/types";
import { useApp } from "./ctx";
import { Dialog } from "./Dialogs";
import * as I from "./icons";
import { Seg } from "./Seg";

const WHEN_KEYS = ["label", "subject", "role", "destination", "purpose"];
const KEY_NAME: Record<string, string> = { label: "Item", subject: "Whose data", role: "Sender", destination: "Sent to", purpose: "Purpose" };
const SUBJECT: Record<string, string> = { individual: "A person", business: "A business", unknown: "Not known" };
const COARSE: Record<string, string> = { "": "Default", year: "Year only", age90: "90 or older" };

type Draft = { id: string; when: Record<string, string[]>; action: string; scope: string; coarse: string; why: string };

function arr(v: string | string[] | undefined | null): string[] { return v === undefined || v === null ? [] : Array.isArray(v) ? v : [v]; }

// a working copy: conditions always as lists, so toggling is simple
function toDraft(r: Rule): Draft {
  const when: Record<string, string[]> = {};
  for (const [k, v] of Object.entries(r.when || {})) when[k] = arr(v);
  return { id: r.id, when, action: r.action, scope: r.scope || "span", coarse: r.coarse || "", why: r.why || "" };
}
function fromDraft(r: Draft): Rule {
  const when: Record<string, string[]> = {};
  for (const k of WHEN_KEYS) if ((r.when[k] || []).length) when[k] = r.when[k];
  const out = { id: r.id.trim(), ...(Object.keys(when).length ? { when } : {}), action: r.action } as Rule;
  if (r.action === "block" && r.scope === "request") out.scope = "request";
  if (r.action === "generalize" && r.coarse) out.coarse = r.coarse;
  out.why = r.why.trim();
  return out;
}

export type Preview = { before: Analysis; after: Analysis };

function PreviewView({ p }: { p: Preview }) {
  const side = (r: Analysis) => r.blocked ? <p className="note-s"><b>Blocked.</b> {r.block_reason ? r.block_reason.why : ""}</p> : <div className="payload">{tokenMarks(r.outbound || "")}</div>;
  const key = (x: { label: string; text: string }) => `${x.label}|${x.text}`, before = new Map(p.before.spans.map((x) => [key(x), x]));
  const changed = p.after.spans.filter((x) => { const b = before.get(key(x)); return !b || act(b, p.before.blocked) !== act(x, p.after.blocked); });
  const list = changed.length ? <ul className="changes">{changed.map((x, n) => {
    const b = before.get(key(x)), now = act(x, p.after.blocked);
    return <li key={n}><span className="chip plain">{label(x.label)}</span> <code>{x.text}</code>: {b ? ACTION[act(b, p.before.blocked)] : "not found"}, now <span className={`chip ${now}`}>{ACTION[now]}</span> by <span className="rule">{x.rule}</span></li>;
  })}</ul> : <p className="note-s">Your edit changes nothing for this message.</p>;
  return <><div className="try-grid"><div><h4>Saved rules</h4>{side(p.before)}</div><div><h4>Your edit</h4>{side(p.after)}</div></div><div><h4>What changed</h4>{list}</div></>;
}

export type Flowish = { role: string; destination: string; purpose: string; useContext: boolean; maxText: number; draftText: string };

// anyone can read the rules; the server decides whether they can be edited
export function RulesDialog({ open, onClose, data, setData, request, flow, refreshMeta, toast }: {
  open: boolean; onClose: () => void; data: PolicyView | null; setData: (d: PolicyView) => void;
  request: { pack?: string; rule?: string; n: number }; flow: Flowish; refreshMeta: () => Promise<void>; toast: (n: ReactNode) => void;
}) {
  const { meta } = useApp();
  const [tab, setTab] = useState("default");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Draft[]>([]);
  const [purposes, setPurposes] = useState<Purpose[]>([]);
  const [error, setError] = useState<ReactNode>(null);
  const [loadError, setLoadError] = useState<ReactNode>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [trying, setTrying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [armed, setArmed] = useState(0);
  const [tryText, setTryText] = useState("");
  const focus = useRef<string | null>(null);
  const flash = useRef<string | null>(null);

  // each open request: reload the rules (unless an edit is under way), pick the pack, then show the rule asked for
  useEffect(() => {
    if (!request.n) return;
    if (editing) { flash.current = request.rule || null; return; }
    setLoading(true);
    setLoadError(null);
    api<PolicyView>("GET", "/api/policies").then((d) => {
      setData(d);
      setTab((cur) => request.pack && d.packs.some((k) => k.id === request.pack) ? request.pack : d.packs.some((k) => k.id === cur) ? cur : "default");
      flash.current = request.rule || null;
    }).catch((e) => setLoadError(errorNode(e))).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request.n]);

  useEffect(() => {
    if (focus.current) { document.getElementById("rules-body")?.querySelector<HTMLElement>(focus.current)?.focus(); focus.current = null; }
    if (flash.current && !loading) {
      const card = document.getElementById(`rule-${flash.current}`);
      flash.current = null;
      if (card) { card.scrollIntoView({ block: "center" }); card.classList.add("flash"); setTimeout(() => card.classList.remove("flash"), 1900); }
    }
  });

  const k = data?.packs.find((x) => x.id === tab);
  const packData = (id: string) => data?.packs.find((x) => x.id === id);
  const valueName = (key: string, v: string) => key === "label" ? label(v) : key === "subject" ? SUBJECT[v] || v : key === "destination" ? destName(v)
    : key === "purpose" ? (meta?.purpose_labels[v] || v) : v;
  // the last rule of a pack that extends nothing must stay a catch-all
  const locked = (i: number) => !k!.extends && i === draft.length - 1;

  const edit = (f: (d: Draft[]) => void, sel?: string) => { const d = draft.map((r) => ({ ...r, when: { ...r.when } })); f(d); setDraft(d); setPreview(null); if (sel) focus.current = sel; };
  const startEdit = () => {
    setEditing(true); setError(null); setPreview(null); setArmed(0);
    setDraft(k!.rules.map(toDraft));
    setPurposes(data!.purposes.map((p) => ({ ...p, omit: [...p.omit] })));
    setTryText((t) => t || flow.draftText);
  };
  const stopEdit = () => { setEditing(false); setError(null); setPreview(null); setArmed(0); };

  const editBody = () => {
    const out: { rules: Rule[]; purposes?: Record<string, { omit: string[] }> } = { rules: draft.map(fromDraft) };
    if (tab === "default") {
      const now = purposes.map((p) => [p.id, p.omit]), was = data!.purposes.map((p) => [p.id, p.omit]);
      if (JSON.stringify(now) !== JSON.stringify(was)) out.purposes = Object.fromEntries(purposes.map((p) => [p.id, { omit: p.omit }]));
    }
    return out;
  };

  const save = async () => {
    setBusy(true); setError(null);
    try {
      setData(await api<PolicyView>("PUT", `/api/policies/${encodeURIComponent(tab)}`, editBody()));
      setBusy(false); stopEdit();
      await refreshMeta();
      toast(<><b>Rules saved.</b> The next message uses them. The change is sealed in the audit log.</>);
    } catch (e) {
      setBusy(false); setError(errorNode(e));
      setTimeout(() => document.getElementById("rules-error")?.scrollIntoView({ block: "center" }));
    }
  };

  const reset = async () => {
    if (!armed) { setArmed(window.setTimeout(() => setArmed(0), 4000)); return; }
    clearTimeout(armed); setArmed(0);
    try {
      setData(await api<PolicyView>("DELETE", `/api/policies/${encodeURIComponent(tab)}`));
      stopEdit();
      await refreshMeta();
      toast(<><b>Shipped rules restored.</b> The reset is sealed in the audit log.</>);
    } catch (e) { setError(errorNode(e)); }
  };

  const tryIt = async () => {
    const text = tryText.trim();
    if (!text) { document.getElementById("try-text")?.focus(); return; }
    setBusy(true); setTrying(true);
    try {
      const p = await api<Preview>("POST", "/api/policies/preview", { ...editBody(), pack: tab, text, role: flow.role,
        destination: flow.destination, purpose: flow.purpose, use_context: flow.useContext });
      setPreview({ before: prepare(p.before), after: prepare(p.after) }); setError(null);
    } catch (e) { setPreview(null); setError(errorNode(e)); }
    setBusy(false); setTrying(false);
    setTimeout(() => (document.getElementById("rules-error") || document.getElementById("try-out"))?.scrollIntoView({ block: "nearest" }));
  };

  const switchTab = (id: string) => { setTab(id); };

  let bar: ReactNode = null, content: ReactNode;
  if (loadError) content = <p className="empty">{loadError}</p>;
  else if (!data || !k || (loading && !editing)) content = <div className="shimmer" style={{ height: 120 }} />;
  else {
    const d = data;
    const tabs = <Seg id="rules-tabs" ariaLabel="Rule set" value={tab} onChange={switchTab}
      options={d.packs.map((p) => ({ v: p.id, label: p.short, disabled: editing && p.id !== tab }))} />;
    const edited = k.edited || (tab === "default" && d.edited_purposes);
    const pill = edited ? <span className="pill edited" title="Changed in this app; saved in data/policies.local.yaml">Edited here</span> : null;
    if (!d.admin) bar = <>{tabs}<span className="grow" />{pill}<span className="note-s">Read only. To edit, start the server with <code>CHAPERONE_ADMIN=1</code>.</span></>;
    else if (!editing) bar = <>{tabs}<span className="grow" />{pill}<button type="button" className="btn btn-quiet" id="rules-edit" onClick={startEdit}>Edit {k.short}</button></>;
    else bar = <>{tabs}<span className="grow" />
      {edited && <button type="button" className="btn btn-ghost" id="rules-reset" onClick={reset}>{armed ? "Click again to reset" : "Reset to shipped rules"}</button>}
      <button type="button" className="btn btn-ghost" id="rules-cancel" onClick={stopEdit}>Cancel</button>
      <button type="button" className="btn btn-primary" id="rules-save" disabled={busy} onClick={save}>Save rules</button></>;

    const parent = k.extends ? packData(k.extends) : null;
    const inherit = parent ? <div className="inherit">Items these rules do not decide go on to the {parent.name} ({plural(parent.rules.length, "rule", "rules")}).
      <button type="button" className="link" disabled={editing} onClick={() => { setTab(parent.id); document.getElementById("rules-dlg")?.scrollTo(0, 0); }}>Show them</button></div> : null;
    const desc = k.description ? <p className="note-s" style={{ marginBottom: 12 }}>{k.description}</p> : null;
    const conds = (when: Rule["when"]) => {
      const keys = WHEN_KEYS.filter((x) => arr((when || {})[x]).length);
      if (!keys.length) return <div className="conds"><span className="cond">Anything the rules above did not decide</span></div>;
      return <div className="conds">{keys.map((x) => <span key={x} className="cond"><b>{KEY_NAME[x]}</b>{arr(when![x]).map((v) => valueName(x, v)).join(", ")}</span>)}</div>;
    };
    const v = d.vocabulary;
    const purposesSec = (isEdit: boolean) => (
      <section className="rules-sec"><h3>What each purpose leaves out</h3>
        <p>Identifiers a purpose does not need are left out before anything is sent. Users can still include one, with a reason that is logged.</p>
        {(isEdit ? purposes : d.purposes).map((p, pi) => (
          <div key={p.id} className="purp"><div><b>{p.label}</b><div className="task">Not needed to {p.task}</div></div>
            <div className="tog-row" role="group" aria-label={`${p.label}: left out`}>{isEdit
              ? v.minimisable.map((x) => <button key={x} type="button" className="tog" data-pi={pi} data-val={x} aria-pressed={p.omit.includes(x)}
                onClick={() => { setPurposes(purposes.map((q, qi) => qi !== pi ? q : { ...q, omit: q.omit.includes(x) ? q.omit.filter((y) => y !== x) : [...q.omit, x] })); setPreview(null); }}>{label(x)}</button>)
              : p.omit.length ? p.omit.map((x) => <span key={x} className="chip omit">{label(x)}</span>) : <span className="any">Nothing</span>}</div></div>
        ))}
      </section>
    );

    if (editing) {
      const last = draft.length - 1, lastMovable = k.extends ? last : last - 1;
      const ruleEdit = (r: Draft, i: number) => {
        const lock = locked(i), moveUp = !lock && i > 0, moveDown = !lock && i < lastMovable;
        const set = (f: keyof Draft, val: string) => edit((dd) => { (dd[i] as Record<string, unknown>)[f] = val; }, `[data-ri="${i}"][data-f="${f}"]`);
        return (
          <li key={i} className="rule-card edit" id={`draft-${i}`}><span className="n">{i + 1}</span><div className="rule-body">
            <div className="fields">
              <label className="field">Rule id<input className="input mono" data-ri={i} data-f="id" value={r.id} maxLength={63} spellCheck={false} autoComplete="off" readOnly={lock}
                onChange={(e) => { const val = e.target.value; setDraft(draft.map((x, n) => n === i ? { ...x, id: val } : x)); setPreview(null); }} /></label>
              <label className="field">Action<select className="select" data-ri={i} data-f="action" value={r.action} onChange={(e) => set("action", e.target.value)}>
                {v.action.map((x) => <option key={x} value={x}>{ACTION[x] || x}</option>)}</select></label>
              {r.action === "block" && <label className="toggle"><input type="checkbox" className="switch" data-ri={i} data-f="scope" checked={r.scope === "request"}
                onChange={(e) => set("scope", e.target.checked ? "request" : "span")} /> Stop the whole message</label>}
              {r.action === "generalize" && <label className="field">How vague<select className="select" data-ri={i} data-f="coarse" value={r.coarse} onChange={(e) => set("coarse", e.target.value)}>
                {Object.keys(COARSE).map((c) => <option key={c} value={c}>{COARSE[c]}</option>)}</select></label>}
              <span className="acts">
                <button type="button" className="icon-btn" data-move={i} data-dir="-1" aria-label={`Move rule ${i + 1} up`} disabled={!moveUp}
                  onClick={() => edit((dd) => { [dd[i], dd[i - 1]] = [dd[i - 1], dd[i]]; }, `[data-move="${i - 1}"][data-dir="-1"]`)}><I.Up /></button>
                <button type="button" className="icon-btn" data-move={i} data-dir="1" aria-label={`Move rule ${i + 1} down`} disabled={!moveDown}
                  onClick={() => edit((dd) => { [dd[i], dd[i + 1]] = [dd[i + 1], dd[i]]; }, `[data-move="${i + 1}"][data-dir="1"]`)}><I.Down /></button>
                <button type="button" className="icon-btn" data-del={i} aria-label={`Delete rule ${i + 1}`} disabled={lock}
                  onClick={() => edit((dd) => { dd.splice(i, 1); }, "#rules-add")}><I.Del /></button>
              </span>
            </div>
            {lock ? <p className="any">Catch-all: it decides every item the rules above do not. It has no conditions and always stays last.</p>
              : <div className="toggles">{WHEN_KEYS.map((key) => {
                const on = r.when[key] || [];
                return [<span key={`${key}-n`}>{KEY_NAME[key]}</span>,
                  <div key={key} className="tog-row" role="group" aria-label={KEY_NAME[key]}>{v[key].map((x) =>
                    <button key={x} type="button" className="tog" data-ri={i} data-key={key} data-val={x} aria-pressed={on.includes(x)}
                      onClick={() => edit((dd) => { dd[i].when[key] = on.includes(x) ? on.filter((y) => y !== x) : [...on, x]; })}>{valueName(key, x)}</button>)}
                    {on.length ? null : <span className="any">any</span>}</div>];
              })}</div>}
            <label className="field">Reason users see<textarea className="input" data-ri={i} data-f="why" maxLength={300} rows={2} value={r.why}
              onChange={(e) => { const val = e.target.value; setDraft(draft.map((x, n) => n === i ? { ...x, why: val } : x)); setPreview(null); }} /></label>
          </div></li>
        );
      };
      const addRule = () => {
        let n = 1;
        while (draft.some((r) => r.id === `new-rule-${n}`)) n += 1;
        edit((dd) => { dd.unshift({ id: `new-rule-${n}`, when: {}, action: "pseudonymize", scope: "span", coarse: "", why: "" }); }, '#draft-0 input[data-f="id"]');
      };
      content = <>
        {error && <div className="callout" role="alert" id="rules-error">{error}</div>}{desc}
        <button type="button" className="btn add-rule" id="rules-add" onClick={addRule}>Add a rule at the top</button>
        <ol className="rules">{draft.map(ruleEdit)}</ol>{inherit}
        {tab === "default" && purposesSec(true)}
        <section className="rules-sec try"><h3>Try your edit</h3>
          <p>Runs this message under the saved rules and under your edit, as <b>{flow.role}</b> to <b>{destLower(flow.destination)}</b>, for {purposeName(meta, flow.purpose)}. Change the flow in the top bar. Nothing is sent or saved.</p>
          <textarea className="input" id="try-text" rows={3} maxLength={flow.maxText} aria-label="Message to try" value={tryText} onChange={(e) => setTryText(e.target.value)} />
          <div><button type="button" className="btn btn-quiet" id="try-go" disabled={busy} onClick={tryIt}>Try it</button></div>
          <div id="try-out">{trying ? <div className="shimmer" style={{ height: 90 }} /> : preview ? <PreviewView p={preview} /> : null}</div></section>
      </>;
    } else {
      content = <>
        {d.error && <div className="callout" role="alert">A rule file changed but has an error, so the previous rules are still in use. {d.error}</div>}{desc}
        <ol className="rules">{k.rules.map((r, i) => (
          <li key={r.id} className="rule-card" id={`rule-${r.id}`}><span className="n">{i + 1}</span><div>
            <div className="top"><span className="rid">{r.id}</span><span className="acts"><span className={`chip ${r.action}`}>{ACTION[r.action] || r.action}</span>
              {r.scope === "request" && <span className="chip plain">Whole message</span>}{r.coarse && <span className="chip plain">{COARSE[r.coarse]}</span>}</span></div>
            {conds(r.when)}<p className="why">{r.why}</p></div></li>
        ))}</ol>{inherit}{tab === "default" && purposesSec(false)}
      </>;
    }
  }
  return (
    <Dialog id="rules-dlg" open={open} onClose={onClose} title="Rules" titleId="rules-title" headClass="rules-h"
      intro="Checked from top to bottom. The first rule that matches an item decides what happens to it."
      bar={<div className="rules-bar" id="rules-bar">{bar}</div>} bodyId="rules-body" live>
      {content}
    </Dialog>
  );
}
