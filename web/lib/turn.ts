import type { ReactNode } from "react";
import type { Baseline, Flow, Result, StepEvent } from "./types";

type Ev<S> = Extract<StepEvent, { step: S }>;

// one message and everything the gateway said about it, filled in as the stream arrives
export type Turn = {
  text: string;
  flow: Flow & { use_context: boolean };
  steps: {
    detect?: Ev<"detect">; decide?: Ev<"decide">; attack: Ev<"attack">[]; ready?: Ev<"ready">;
    guard?: Ev<"guard">; reply?: Ev<"reply">; restore?: Ev<"restore">;
  };
  result: Result | null;
  error: ReactNode;
  baseline: undefined | "loading" | null | Baseline;
  open: Set<string>;  // which Details panels the reader opened
  follow: boolean;  // keep it in view while it is live
};
