import { createContext, useContext } from "react";
import type { Meta, PolicyView } from "@/lib/types";

// what every part of the page reads: the gateway's meta, the rule list, and how to open a rule
export type App = {
  meta: Meta | null;  // null until the gateway answers /api/meta
  rules: PolicyView | null;
  openRules: (pack?: string, rule?: string) => void;
};

export const AppCtx = createContext<App | null>(null);

export function useApp(): App {
  const v = useContext(AppCtx);
  if (!v) throw new Error("useApp outside AppCtx");
  return v;
}

// which pack holds this rule, following "extends"; null for the gateway's own decisions (purpose, attacker, session)
export function rulePack(rules: PolicyView | null, id: string, packId: string, seen = 0): string | null {
  const k = rules && rules.packs.find((x) => x.id === packId);
  if (!k || seen > 8) return null;
  if (k.rules.some((r) => r.id === id)) return k.id;
  return k.extends ? rulePack(rules, id, k.extends, seen + 1) : null;
}

export function RuleRef({ id, pack }: { id: string; pack?: string }) {
  const { rules, openRules } = useApp();
  const at = rulePack(rules, id, pack || "default");
  return at ? <button type="button" className="rule-link" title="Show this rule" onClick={() => openRules(at, id)}>{id}</button>
    : <span className="rule">{id}</span>;
}
