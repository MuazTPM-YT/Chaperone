"use client";
import { useCallback, useEffect, useLayoutEffect, useReducer, useRef, useState, type ReactNode } from "react";
import { AppCtx } from "@/components/ctx";
import { CompareDialog, PersonDialog, sealText, type CompareState } from "@/components/Dialogs";
import * as I from "@/components/icons";
import { RulesDialog } from "@/components/RulesDialog";
import { Seg } from "@/components/Seg";
import { TurnView, type TurnActions } from "@/components/Turn";
import { api, errorNode, post, stream } from "@/lib/api";
import { CAT, cap, destLower, destName, maxText, newId, packNote, prepare, purposeName } from "@/lib/text";
import type { Turn } from "@/lib/turn";
import type { Analysis, Baseline, LogCheck, Meta, PolicyView, Scenario } from "@/lib/types";

type Include = { label: string; text: string; reason: string };
type Draft = { text: string; role: string; destination: string; purpose: string; pack: string; use_context: boolean; include: Include[] };

const THEMES = ["auto", "light", "dark"] as const;
type Theme = (typeof THEMES)[number];
const SAYS: Record<string, string> = { detect: "Sensitive items found.", decide: "Rules applied.", guard: "Final check passed. Sent.", reply: "The AI replied.", restore: "Real values put back." };
const START = "uv run --frozen python -m chaperone";

function storedTheme(): Theme { try { return (localStorage.getItem("fg-theme") as Theme) || "auto"; } catch { return "auto"; } }

// the browser bar matches the page: per scheme when automatic, the chosen colour otherwise
function applyTheme(t: Theme) {
  if (t === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", t);
  for (const m of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) {
    const dark = m.media.includes("dark");
    m.content = t === "auto" ? (dark ? "#0f1115" : "#fcfcfd") : t === "dark" ? "#0f1115" : "#fcfcfd";
  }
}

export default function Page() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [down, setDown] = useState(false);
  const [data, setDataSet] = useState("demo");
  const [role, setRole] = useState("");
  const [purpose, setPurpose] = useState("");
  const [dest, setDest] = useState("external");
  const [pack, setPack] = useState("default");
  const [useCtx, setUseCtx] = useState(true);
  const [text, setText] = useState("");
  const [busy, setBusyState] = useState(false);
  const [ctx, setCtx] = useState<{ ok: boolean; err: string } | null>(null);
  const [current, setCurrent] = useState("");
  const [railOpen, setRailOpen] = useState(false);
  const [narrow, setNarrow] = useState(false);
  const [theme, setTheme] = useState<Theme>("auto");
  const [live, setLive] = useState("");
  const [toastNode, setToastNode] = useState<ReactNode>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compare, setCompare] = useState<CompareState>({ status: "idle", runs: [] });
  const [personOpen, setPersonOpen] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [rulesReq, setRulesReq] = useState<{ pack?: string; rule?: string; n: number }>({ n: 0 });
  const [rules, setRules] = useState<PolicyView | null>(null);
  const [, bump] = useReducer((x: number) => x + 1, 0);

  const turns = useRef<Turn[]>([]);
  const session = useRef(newId());
  const includes = useRef<Include[]>([]);  // "include anyway" choices for the message being sent again
  const busyRef = useRef(false);
  const toastTimer = useRef(0);
  const mainRef = useRef<HTMLElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const railRef = useRef<HTMLElement>(null);

  const setBusy = (b: boolean) => { busyRef.current = b; setBusyState(b); };
  const toast = useCallback((node: ReactNode) => {
    clearTimeout(toastTimer.current);
    setToastNode(node);
    toastTimer.current = window.setTimeout(() => setToastNode(null), 9000);
  }, []);
  const closeRail = () => setRailOpen(false);
  const openRules = useCallback((p?: string, rule?: string) => {
    setRailOpen(false);
    setRulesOpen(true);
    setRulesReq((r) => ({ pack: p, rule, n: r.n + 1 }));
  }, []);

  // fill the role and purpose lists and the rules switch; keeps the current choices when they still exist
  const applyMeta = (m: Meta) => {
    setMeta(m);
    setRole((r) => m.roles.includes(r) ? r : m.roles[0] || "");
    setPurpose((p) => m.purposes.includes(p) ? p : m.purposes[0] || "");
    setPack((k) => m.packs.some((x) => x.id === k) ? k : "default");
  };
  const refreshMeta = async () => {
    try { applyMeta(await (await fetch(`/api/meta?data=${encodeURIComponent(data)}`)).json()); } catch { /* keep the lists we have */ }
  };
  const loadRules = () => api<PolicyView>("GET", "/api/policies").then(setRules);

  // ---------- requests ----------
  const stopFollow = () => { for (const t of turns.current) t.follow = false; };

  const loadBaseline = async (t: Turn, body: object) => {
    const r = t.result!;
    if (r.flow.destination !== "external" || !r.attack || !r.attack.ran) return;
    t.baseline = "loading";
    bump();
    try { t.baseline = await (await post("/api/baseline", body, maxText(meta))).json() as Baseline; } catch { t.baseline = null; }
    if (turns.current.includes(t)) bump();
  };

  const send = async (d: Draft) => {
    const msg = d.text.trim();
    if (busyRef.current || !msg) return;
    const body = { session_id: session.current, text: msg, role: d.role, destination: d.destination, purpose: d.purpose, pack: d.pack,
      use_context: d.use_context, include: d.include };
    const t: Turn = { text: msg, flow: { role: d.role, destination: d.destination, purpose: d.purpose, pack: d.pack, use_context: d.use_context },
      steps: { attack: [] }, result: null, error: null, baseline: undefined, open: new Set(), follow: true };
    stopFollow();
    turns.current = [...turns.current, t];
    setBusy(true);
    setText("");
    includes.current = [];
    bump();
    try {
      await stream("/api/chat/stream", body, maxText(meta), (e) => {
        if (e.step === "attack") t.steps.attack.push(e);
        else if (e.step === "result") { t.result = prepare(e.result); setCtx({ ok: t.result.context_ok, err: t.result.context_error }); }
        else if (e.step === "error") t.error = `The gateway failed (${e.error}). Its terminal shows the details.`;
        else (t.steps as Record<string, unknown>)[e.step] = e;
        if (SAYS[e.step]) setLive(SAYS[e.step]);
        bump();
      });
    } catch (e) {
      t.error = errorNode(e);
      bump();
    }
    setBusy(false);
    if (t.error) setText((cur) => cur || msg);
    if (t.result) {
      setLive(t.result.blocked ? "Blocked. Nothing left this laptop." : t.result.sent ? "Reply ready with real values." : "Not sent.");
      loadBaseline(t, body);
    }
  };

  const draft = (over: Partial<Draft> = {}): Draft => ({ text, role, destination: dest, purpose, pack, use_context: useCtx, include: includes.current, ...over });

  const runCompare = async (msg: string, flows: Scenario["compare"] | null, p = pack) => {
    const value = msg.trim();
    if (!value || busyRef.current) return;
    setBusy(true);
    setCompare({ status: "loading", runs: [] });
    setCompareOpen(true);
    try {
      const out = await (await post("/api/compare", { text: value, pack: p, use_context: useCtx, ...(flows ? { flows } : {}) }, maxText(meta))).json() as { runs: Analysis[] };
      setCompare({ status: "idle", runs: out.runs.map(prepare) });
    } catch (e) {
      setCompare({ status: "error", runs: [], error: errorNode(e) });
    }
    setBusy(false);
  };

  const newConversation = () => {
    fetch(`/api/reset/${session.current}`, { method: "POST" }).catch(() => {});
    session.current = newId();
    turns.current = [];
    includes.current = [];
    bump();
  };

  const runPreset = (id: string, m = meta) => {
    const s = m && m.scenarios.find((x) => x.id === id);
    if (!s || busyRef.current) return;
    setCurrent(id);
    closeRail();
    newConversation();  // each scenario starts clean, so placeholders count from 1
    setText(s.text);
    setRole(s.role);
    setPurpose(s.purpose);
    setDest(s.destination);
    setPack(s.pack || "default");
    if (s.compare) runCompare(s.text, s.compare, s.pack || "default");
    else send({ text: s.text, role: s.role, destination: s.destination, purpose: s.purpose, pack: s.pack || "default", use_context: useCtx, include: [] });
  };

  const verifyLog = async () => {
    try {
      const res = await fetch("/api/audit/verify");
      if (!res.ok) throw new Error(`The gateway answered with error ${res.status}.`);
      const log = await res.json() as LogCheck;
      toast(<><b>{log.ok ? "Audit log seal intact." : "Audit log seal broken."}</b> {sealText(log)}</>);
    } catch (e) {
      toast(<><b>The seal check did not run.</b> {e instanceof Error ? e.message : String(e)}</>);
    }
  };

  const actions: TurnActions = {
    busy,
    onToggle: (t, key, open) => { if (open) t.open.add(key); else t.open.delete(key); },
    onInclude: (t, item, reason) => {
      if (busyRef.current) return;
      const next = includes.current.filter((x) => !(x.label === item.label && x.text === item.text)).concat([{ ...item, reason }]);
      setText(t.text);
      send(draft({ text: t.text, include: next }));
    },
    onCopy: async (t) => {
      try { await navigator.clipboard.writeText(t.result!.restored || ""); return true; }
      catch { toast("Could not copy. Select the reply text and copy it instead."); return false; }
    },
  };

  // ---------- boot ----------
  useEffect(() => {
    const th = storedTheme();
    setTheme(th);
    applyTheme(th);
    const dataSet = new URLSearchParams(location.search).get("data") || "demo";
    setDataSet(dataSet);
    const mq = matchMedia("(max-width: 1360px)");
    setNarrow(mq.matches);
    const onMq = () => { setNarrow(mq.matches); if (!mq.matches) setRailOpen(false); };
    mq.addEventListener("change", onMq);
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setRailOpen(false); };
    document.addEventListener("keydown", onKey);
    (async () => {
      let m: Meta;
      try { m = await (await fetch(`/api/meta?data=${encodeURIComponent(dataSet)}`)).json(); }
      catch { setDown(true); return; }
      applyMeta(m);
      setDest("external");
      setPack("default");
      setCtx({ ok: true, err: "" });
      loadRules().catch(() => {});  // rule links in Details need the rule list; the panel reloads it when opened
      // #8a runs scenario 8a, handy for recording; #rules opens the rules panel
      if (location.hash === "#rules") openRules("default");
      else if (location.hash) runPreset(decodeURIComponent(location.hash.slice(1)), m);
      else textRef.current?.focus();
    })();
    return () => { mq.removeEventListener("change", onMq); document.removeEventListener("keydown", onKey); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // the composer floats over the lanes: the lanes leave room for it, and it stops at the scrollbar
  useLayoutEffect(() => {
    const measure = () => {
      mainRef.current!.style.setProperty("--composer-h", `${formRef.current!.offsetHeight}px`);
      mainRef.current!.style.setProperty("--sb", `${stageRef.current!.offsetWidth - stageRef.current!.clientWidth}px`);
    };
    const ro = new ResizeObserver(measure);
    ro.observe(formRef.current!);
    ro.observe(stageRef.current!);
    return () => ro.disconnect();
  }, []);

  useEffect(() => { if (railOpen) railRef.current?.focus({ preventScroll: true }); }, [railOpen]);

  const cycleTheme = () => {
    const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    try { localStorage.setItem("fg-theme", next); } catch { /* private mode: the choice lasts this page only */ }
    setTheme(next);
    applyTheme(next);
  };

  // ---------- view ----------
  const list = turns.current;
  const empty = !list.length;
  const max = maxText(meta);
  const blank = !text.trim();
  const endpoint = meta?.endpoints[dest];
  const where = endpoint ? (endpoint.simulated ? (dest === "external" ? "simulated on this laptop" : "inside the organisation") : `at ${endpoint.host}`) : "";
  const themeName = theme === "auto" ? "automatic" : theme;
  const ctxState = !ctx ? "starting" : ctx.ok ? `${meta?.context_model}, on this laptop` : ctx.err === "disabled" ? "turned off" : "offline";
  const sub = (s: Scenario) => s.compare ? "three flows side by side" : `${s.role} to ${destLower(s.destination)}, ${purposeName(meta, s.purpose)}${packNote(meta, s.pack)}`;
  const groups: { name: string; items: Scenario[] }[] = [];
  for (const s of meta?.scenarios || []) {
    let g = groups.find((x) => x.name === s.group);
    if (!g) groups.push(g = { name: s.group, items: [] });
    g.items.push(s);
  }
  // the four that show the idea fastest; any scenario id missing from the data set is skipped
  const featured = ["1b", "8a", "7", "2b"].map((id) => meta?.scenarios.find((s) => s.id === id)).filter((s): s is Scenario => Boolean(s));
  const picks = featured.length ? featured : (meta?.scenarios || []).slice(0, 4);
  const lastResult = [...list].reverse().find((x) => x.result)?.result;
  const exposure = lastResult?.exposure || [];

  const page = (
    <div className="app">
      <header className="topbar">
        <button type="button" className="icon-btn" id="rail-open" aria-label="Scenarios and tools" aria-controls="rail" aria-expanded={railOpen} onClick={() => setRailOpen(true)}>
          <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 6h13M3.5 10h13M3.5 14h13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
        </button>
        <a className="brand" href="/" aria-label="Chaperone, start over">
          {/* mark: data crossing a dashed boundary, the one idea the product is about */}
          <svg width="28" height="28" viewBox="0 0 30 30" aria-hidden="true"><rect x="0.5" y="0.5" width="29" height="29" rx="8.5" fill="var(--ink)" /><path d="M15 6v18" stroke="var(--paper)" strokeOpacity=".55" strokeWidth="1.6" strokeDasharray="2.4 2.2" /><path d="M7.5 15h14.5m-4.5-4.5L22 15l-4.5 4.5" fill="none" stroke="var(--paper)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <b>Chaperone</b>
        </a>
        <div className="flow" role="group" aria-label="Flow: who sends, to where, for what">
          <select id="role" className="select" aria-label="Sender role" value={role} onChange={(e) => setRole(e.target.value)}>
            {(meta?.roles || []).map((r) => <option key={r}>{r}</option>)}
          </select>
          <span>sends to</span>
          <Seg id="dest" ariaLabel="Destination" value={dest} onChange={setDest}
            options={[{ v: "internal", label: "Internal model" }, { v: "external", label: "External AI" }]} />
          <span>for</span>
          <select id="purpose" className="select" aria-label="Purpose: what the data may be used for" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
            {(meta?.purposes || []).map((p) => <option key={p} value={p}>{meta!.purpose_labels[p] || p}</option>)}
          </select>
          <span>under</span>
          <Seg id="pack" ariaLabel="Rules" value={pack} onChange={setPack}
            options={(meta?.packs || []).map((k) => ({ v: k.id, label: k.short, title: k.description || undefined }))} />
        </div>
        <div className="status">
          <span id="ctx-status" title={`Local AI check: ${ctx?.ok ? meta?.context_model : ctxState}`}><span className={`dot${!ctx || ctx.ok ? "" : " off"}`} /><span className="txt">Local AI check: {ctxState}</span></span>
          <button type="button" className="icon-btn" id="theme" aria-label={`Theme: ${themeName}`} title={`Theme: ${themeName}`} onClick={cycleTheme}>
            {theme === "auto" ? <I.Auto /> : theme === "light" ? <I.Sun /> : <I.Moon />}
          </button>
        </div>
      </header>

      <div className="body">
        <aside className={`rail-side${railOpen ? " open" : ""}`} id="rail" aria-label="Scenarios and tools" tabIndex={-1} ref={railRef} inert={narrow && !railOpen}>
          <button type="button" className="btn btn-quiet new-chat" id="reset" onClick={() => {
            if (busyRef.current) return;
            newConversation();
            setCurrent("");
            closeRail();
            textRef.current?.focus();
          }}>
            <svg width="16" height="16" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4.5v11M4.5 10h11" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" /></svg>New chat</button>
          <h2>Demo scenarios</h2>
          <div id="scenarios">{groups.map((g) => (
            <div key={g.name} className="sc-group"><p>{g.name.replace(/^\d+\.\s*/, "")}</p>{g.items.map((s) =>
              <button key={s.id} type="button" data-id={s.id} aria-current={current === s.id} onClick={() => runPreset(s.id)}>{s.title}<small>{sub(s)}</small></button>)}</div>
          ))}</div>
          <div id="ledger-block" hidden={!lastResult || lastResult.flow.destination !== "external"}>
            <h2>What the external AI could know</h2>
            <ul className="ledger" id="ledger">{exposure.length ? exposure.map((e, n) =>
              <li key={n}><b>{CAT[e.category] || e.category}: {e.guess}</b><span>{cap(e.status)}, message {e.turn}</span></li>)
              : <li><span>Nothing inferred about anyone yet in this chat.</span></li>}</ul>
          </div>
          <h2>Rules</h2>
          <div className="tools">
            <button type="button" className="btn btn-ghost" id="rules-open" onClick={() => openRules(pack)}><span id="rules-open-label">{rules?.admin ? "View and edit the rules" : "View the rules"}</span><span className="dot off" id="rules-dot" hidden={!rules?.error} title="The rule file has an error" /></button>
          </div>
          <h2>Records</h2>
          <div className="tools">
            <button type="button" className="btn btn-ghost" id="person-open" onClick={() => { closeRail(); setPersonOpen(true); }}>Person report</button>
            <button type="button" className="btn btn-ghost" id="verify" onClick={() => { closeRail(); verifyLog(); }}>Check the audit log seal</button>
            <a className="btn btn-ghost" href="/api/records.csv" download>Download processing record (CSV)</a>
          </div>
          <h2>What the actions mean</h2>
          <div className="legend">
            <div><span className="chip pass">Allowed</span>sent as typed</div>
            <div><span className="chip pseudonymize">Masked</span>a placeholder goes out; the real value comes back in the reply</div>
            <div><span className="chip generalize">Made vague</span>a vaguer version goes out; the exact value stays here</div>
            <div><span className="chip omit">Left out</span>the purpose does not need it</div>
            <div><span className="chip block">Blocked</span>removed, or the whole request stopped</div>
          </div>
        </aside>
        <div className={`scrim${railOpen ? " open" : ""}`} id="scrim" onClick={closeRail} />

        <main className={`stage-wrap${empty ? " is-empty" : ""}`} id="main" ref={mainRef}>
          <div className="stage" id="stage" ref={stageRef} onWheel={stopFollow} onTouchMove={stopFollow} onKeyDown={stopFollow}>
            <div className="lanes" id="lanes">
              <div className="lane-heads">
                <div className="lane-head you"><h2><span className="glyph" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="4" r="2.3" fill="currentColor" /><path d="M1.8 11a4.2 4.2 0 0 1 8.4 0" fill="currentColor" /></svg></span>You</h2><p>Real names and values, on this laptop</p></div>
                <div className="lane-head mid"><h2><span className="glyph" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 12 12"><path d="M6 1 10.5 2.8v3.1C10.5 8.6 8.6 10.4 6 11 3.4 10.4 1.5 8.6 1.5 5.9V2.8Z" fill="currentColor" /></svg></span>Chaperone</h2><p>Checks on this laptop</p></div>
                <div className="lane-head ai"><h2 id="ai-name">{destName(dest)}<span className="glyph" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 12 12"><path d="M6 1.5 7.1 4.9 10.5 6 7.1 7.1 6 10.5 4.9 7.1 1.5 6 4.9 4.9Z" fill="currentColor" /></svg></span></h2>
                  <p id="ai-where">{endpoint ? `${endpoint.model || "model not set"}, ${where}` : "Outside this laptop"}</p></div>
              </div>
              <section className="hero" id="hero" hidden={!empty}>
                <h1>You see real names.<span>The AI sees only what it needs.</span></h1>
                <p>{down ? <>The gateway is not running. Start it with <code>{START}</code> and reload this page.</>
                  : "Chaperone sits between your team and an AI chatbot. Before a message leaves, it finds names, IDs and sensitive details, applies your rules for this flow, and tries to work out who and what the message is about. The reply comes back with the real values put in again."}</p>
                <div className="picks" id="picks">{picks.map((s) =>
                  <button key={s.id} type="button" className="pick" data-id={s.id} onClick={() => runPreset(s.id)}><b>{s.title}</b><span>{sub(s)}</span></button>)}</div>
                <p className="how">Pick a scenario, or type below. The flow at the top decides what may leave: who sends it, where it goes, and why.</p>
              </section>
              {meta && list.map((t, i) => <TurnView key={i} t={t} i={i} turns={list} a={actions} />)}
            </div>
          </div>

          <form className="composer" id="form" ref={formRef} onSubmit={(e) => { e.preventDefault(); send(draft()); }}>
            <div className="box">
              <textarea id="text" ref={textRef} rows={1} maxLength={max} enterKeyHint="send" aria-label="Message" placeholder="Message the AI. Chaperone checks it first."
                value={text} onChange={(e) => { includes.current = []; setText(e.target.value); }}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(draft()); } }} />
              <div className="box-row">
                <label className="toggle"><input type="checkbox" className="switch" id="use-ctx" checked={useCtx} onChange={(e) => setUseCtx(e.target.checked)} /> <span><span className="wide">Local </span>AI checks</span></label>
                <button className="btn btn-ghost" id="compare" type="button" disabled={busy || blank} onClick={() => runCompare(text, null)}><span>Compare<span className="wide"> three</span> flows</span></button>
                <span className="grow" />
                <button className="btn btn-primary send" id="send" type="submit" disabled={busy || blank} aria-busy={busy} aria-label={busy ? "Checking" : "Check and send"}>
                  {busy ? <I.Busy /> : <I.Send />}
                </button>
              </div>
            </div>
            <div className="hints">
              <span id="purpose-line">{purpose === "general" || !purpose ? (purpose ? "No purpose stated, so nothing is left out for being unneeded." : "")
                : `Purpose: ${purposeName(meta, purpose)}. Identifiers it does not need are left out.`}</span>
              <span className="keys"><kbd>Enter</kbd> sends, <kbd>Shift</kbd> + <kbd>Enter</kbd> adds a line</span>
              <span className="warn" id="count" hidden={text.length < max * 0.85}>{`${text.length.toLocaleString("en-IN")} / ${max.toLocaleString("en-IN")} characters`}</span>
            </div>
          </form>
        </main>
      </div>
    </div>
  );

  return (
    <AppCtx.Provider value={{ meta, rules, openRules }}>
      {page}
      {meta && <>
        <CompareDialog open={compareOpen} onClose={() => setCompareOpen(false)} state={compare} />
        <RulesDialog open={rulesOpen} onClose={() => setRulesOpen(false)} data={rules} setData={setRules} request={rulesReq}
          flow={{ role, destination: dest, purpose, useContext: useCtx, maxText: max, draftText: text.trim() || (list.length ? list[list.length - 1].text : "") }}
          refreshMeta={refreshMeta} toast={toast} />
        <PersonDialog open={personOpen} onClose={() => setPersonOpen(false)} />
      </>}
      <div id="toast-slot" aria-live="polite">{toastNode && <div className="toast" role="status"><span>{toastNode}</span>
        <button type="button" aria-label="Dismiss" onClick={() => setToastNode(null)}><I.Stop /></button></div>}</div>
      <div className="sr" id="live" aria-live="polite">{live}</div>
      {meta?.dev && <nav className="devdata" aria-label="Dev data set">{[["demo", "Demo data"], ["worst", "Worst case"]].map(([v, l]) =>
        <a key={v} href={`?data=${v}`} aria-current={data === v}>{l}</a>)}</nav>}
    </AppCtx.Provider>
  );
}
