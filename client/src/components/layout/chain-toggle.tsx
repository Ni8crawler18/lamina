"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useChain } from "@/contexts/chain-context";

export default function ChainToggle() {
  const { active, chains, setChain } = useChain();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/40 px-2.5 py-1.5 text-xs transition-colors hover:border-border hover:bg-card/70"
      >
        <img src={`${active.logo}?v=7`} alt="" className={`h-4 w-4 object-contain ${active.family === "hedera" ? "scale-[0.82]" : ""}`} />
        <span className="font-medium">{active.name}</span>
        <ChevronDown className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-1.5 w-56 overflow-hidden rounded-xl border border-border/60 bg-popover/95 p-1 shadow-xl backdrop-blur">
          <p className="px-2.5 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/70">Active network</p>
          {chains.map((c) => (
            <button
              key={c.slug}
              onClick={() => { setChain(c.slug); setOpen(false); }}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors hover:bg-card/70"
            >
              <img src={`${c.logo}?v=7`} alt="" className={`h-4 w-4 object-contain ${c.family === "hedera" ? "scale-[0.82]" : ""}`} />
              <span className="flex-1">
                <span className="block leading-tight">{c.name}</span>
                {c.note && <span className="block text-[10px] leading-tight text-muted-foreground/70">{c.note}</span>}
              </span>
              {c.slug === active.slug && <Check className="h-3.5 w-3.5 text-violet" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
