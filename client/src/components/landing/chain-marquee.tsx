"use client";

import { CHAINS } from "@/lib/chains";

/** Infinite left-scrolling marquee of the networks Lamina runs on (logos recolored to theme).
 *  Plain <img> on purpose — bypasses the next/image optimizer cache. */
export function ChainMarquee() {
  const row = [...CHAINS, ...CHAINS];
  return (
    <div className="relative w-full overflow-hidden py-2">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-40 bg-gradient-to-r from-background to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-40 bg-gradient-to-l from-background to-transparent" />

      <div className="flex w-max items-center gap-12 [animation:ticker_42s_linear_infinite] hover:[animation-play-state:paused]">
        {row.map((c, i) => (
          <div key={`${c.slug}-${i}`} className="flex shrink-0 items-center gap-3 opacity-75 transition-opacity hover:opacity-100">
            <img src={`${c.logo}?v=6`} alt={c.name} className={`h-7 w-7 object-contain ${c.slug === "hedera-testnet" ? "scale-[0.82]" : ""}`} />
            <span className="whitespace-nowrap text-base font-light tracking-tight text-foreground/85">{c.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
