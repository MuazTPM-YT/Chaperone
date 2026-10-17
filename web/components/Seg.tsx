import { useLayoutEffect, useRef } from "react";

export type SegOption = { v: string; label: string; title?: string; disabled?: boolean };

// segmented control: the thumb slides to the pressed button; re-measured whenever the control changes size
export function Seg({ id, ariaLabel, value, options, onChange }: {
  id: string; ariaLabel: string; value: string; options: SegOption[]; onChange: (v: string) => void;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const seg = ref.current!;
    const place = () => {
      const on = seg.querySelector<HTMLButtonElement>('button[aria-pressed="true"]');
      const thumb = seg.querySelector<HTMLElement>(".thumb");
      if (on && thumb && on.offsetWidth) { thumb.style.width = `${on.offsetWidth}px`; thumb.style.transform = `translateX(${on.offsetLeft}px)`; }
    };
    place();
    const ro = new ResizeObserver(place);
    ro.observe(seg);
    document.fonts?.ready.then(place);
    return () => ro.disconnect();
  }, [value, options]);
  return (
    <span className="seg" id={id} role="group" aria-label={ariaLabel} ref={ref}>
      <span className="thumb" aria-hidden="true" />
      {options.map((o) => (
        <button key={o.v} type="button" data-v={o.v} title={o.title} disabled={o.disabled} aria-pressed={o.v === value}
          onClick={() => { if (o.v !== value) onChange(o.v); }}>{o.label}</button>
      ))}
    </span>
  );
}
