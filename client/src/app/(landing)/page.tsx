"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ChainMarquee } from "@/components/landing/chain-marquee";
import { CHAINS } from "@/lib/chains";

const ARBISCAN_FACTORY =
  "https://sepolia.arbiscan.io/address/0x8610E57f1357a41c2991ba64764c2Fdc8b2DD33e#code";

export default function Landing() {
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add("is-visible")),
      { threshold: 0.15 }
    );
    document.querySelectorAll(".on-scroll").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-background text-foreground">
      <div className="bg-grain" />
      <Nav />
      <Hero />

      <section className="relative mx-auto max-w-7xl px-6 pb-14">
        <p className="mb-6 text-center text-[11px] uppercase tracking-[0.32em] text-muted-foreground">
          Deployed across 8 networks · every major EVM chain and Hedera
        </p>
        <ChainMarquee />
      </section>

      <Stats />
      <Lifecycle />
      <MultiChain />
      <Surfaces />
      <Trust />
      <CTA />
      <Footer />
    </main>
  );
}

function Logo({ size = 28 }: { size?: number }) {
  return <img src="/logo.svg" alt="Lamina" width={size} height={size} style={{ width: size, height: size }} />;
}

function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/50 bg-background/60 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="text-lg font-medium tracking-tight">Lamina</span>
        </Link>
        <div className="hidden items-center gap-9 text-sm text-muted-foreground md:flex">
          <a href="#lifecycle" className="transition-colors hover:text-foreground">Lifecycle</a>
          <a href="#chains" className="transition-colors hover:text-foreground">Networks</a>
          <a href="#surfaces" className="transition-colors hover:text-foreground">Integrations</a>
          <a href="#trust" className="transition-colors hover:text-foreground">Compliance</a>
        </div>
        <Link
          href="/dashboard"
          className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:shadow-[0_0_24px_hsl(var(--violet)/0.5)]"
        >
          Launch App
        </Link>
      </nav>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative">
      <div className="absolute inset-0 bg-vault-grid" />
      <div className="aura aura-violet left-[-12%] top-[-15%] h-[620px] w-[620px]" />
      <div className="aura aura-cyan right-[-10%] top-[10%] h-[480px] w-[480px]" />

      <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-6 pb-20 pt-24 lg:grid-cols-[1.02fr_0.98fr] lg:pt-32">
        <div>
          <h1 className="reveal reveal-1 text-6xl font-extralight leading-[1.02] tracking-tight sm:text-7xl lg:text-[5rem]">
            The autonomous
            <br />
            <span className="text-iris font-light">back office</span>
            <br />
            for tokenized assets.
          </h1>

          <p className="reveal reveal-2 mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground">
            Lamina is the lifecycle layer for tokenized securities. Issue an{" "}
            <span className="text-foreground">ERC-3643</span> permissioned token, and the agent
            enforces KYC and OFAC SDN screening on every transfer, distributes USDC coupons, updates
            NAV, and settles redemption at maturity — on any EVM network or Hedera, with an
            access-controlled on-chain audit trail.
          </p>

          <div className="reveal reveal-3 mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/dashboard"
              className="group rounded-full bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-all hover:shadow-[0_0_34px_hsl(var(--violet)/0.5)]"
            >
              Launch the agent
              <span className="ml-2 inline-block transition-transform group-hover:translate-x-0.5">→</span>
            </Link>
            <a
              href={ARBISCAN_FACTORY}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-border bg-card/40 px-6 py-3 text-sm text-foreground/90 transition-colors hover:border-violet/50"
            >
              View source-verified contracts
            </a>
          </div>

          <div className="reveal reveal-4 mt-11 flex flex-wrap items-center gap-x-8 gap-y-3 text-xs tracking-wide text-muted-foreground">
            <Proof value="ERC-3643" label="+ Hedera HTS" />
            <Proof value="8" label="networks" />
            <Proof value="19" label="contract tests, source-verified" />
          </div>
        </div>

        <StackedGlass />
      </div>
    </section>
  );
}

function Proof({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-violet">{value}</span>
      <span className="text-muted-foreground/70">{label}</span>
    </div>
  );
}

function StackedGlass() {
  const layers = Array.from({ length: 14 });
  return (
    <div className="reveal reveal-2 relative mx-auto aspect-square w-full max-w-[540px]">
      <div className="aura aura-violet left-1/2 top-1/2 h-[340px] w-[340px] -translate-x-1/2 -translate-y-1/2" />
      <div className="aura aura-cyan left-[55%] top-[60%] h-[220px] w-[220px]" />
      <div className="absolute inset-0 grid place-items-center" style={{ perspective: "1500px" }}>
        <div className="relative" style={{ transformStyle: "preserve-3d", animation: "stack-float 9s ease-in-out infinite" }}>
          {layers.map((_, i) => {
            const mid = (layers.length - 1) / 2;
            const z = (i - mid) * 17;
            const isAccent = i % 4 === 0;
            return (
              <div
                key={i}
                className="absolute left-1/2 top-1/2 h-[150px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-[14px] glass"
                style={{
                  transform: `translateZ(${z}px)`,
                  borderColor: isAccent ? "hsl(var(--cyan) / 0.35)" : "hsl(var(--violet) / 0.18)",
                  boxShadow: isAccent
                    ? "0 0 30px hsl(var(--cyan) / 0.14), inset 0 1px 0 hsl(var(--cyan) / 0.4)"
                    : "inset 0 1px 0 hsl(var(--violet) / 0.25)",
                  opacity: 0.5 + (i / layers.length) * 0.5,
                }}
              >
                <span className="absolute left-5 top-1/2 h-px w-2/3" style={{ background: "linear-gradient(90deg, hsl(var(--cyan)/0.5), transparent)" }} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Stats() {
  const stats = [
    { v: "$24B", l: "tokenized RWA on-chain", s: "≈5× in 3 years · rwa.xyz" },
    { v: "$16T", l: "tokenized RWA by 2030", s: "BCG estimate" },
    { v: "8", l: "networks, one engine", s: "EVM + non-EVM Hedera" },
    { v: "6", l: "lifecycle stages automated", s: "issuance → redemption" },
  ];
  return (
    <section className="border-y border-border/50 bg-card/15">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-px bg-border/30 md:grid-cols-4">
        {stats.map((s, i) => (
          <div key={i} className="on-scroll bg-background px-6 py-10" style={{ transitionDelay: `${i * 70}ms` }}>
            <div className="text-5xl font-extralight text-iris tabular">{s.v}</div>
            <div className="mt-3 text-sm text-foreground/90">{s.l}</div>
            <div className="mt-1 text-[11px] uppercase tracking-wider text-muted-foreground">{s.s}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Lifecycle() {
  const steps = [
    { n: "01", t: "Issue", d: "Deploy an ERC-3643 permissioned token and a dedicated audit topic in a single factory transaction." },
    { n: "02", t: "Onboard", d: "Grant on-chain KYC after automated OFAC SDN screening of investor names and wallet addresses." },
    { n: "03", t: "Enforce", d: "Validate every transfer in the token's transfer hook — KYC, jurisdiction (Reg D / Reg S), lock-ups, holder caps." },
    { n: "04", t: "Distribute", d: "Pay coupons and dividends to holders pro-rata in USDC (ERC-20)." },
    { n: "05", t: "Revalue", d: "Update net asset value from a treasury-yield oracle." },
    { n: "06", t: "Settle", d: "At maturity, claw back holdings via forceBurn, return principal in USDC, and retire supply." },
  ];
  return (
    <section id="lifecycle" className="mx-auto max-w-7xl px-6 py-28">
      <SectionHead eyebrow="The lifecycle" title="One instruction. The full regulated lifecycle." />
      <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-border/50 bg-border/30 sm:grid-cols-2 lg:grid-cols-3">
        {steps.map((s, i) => (
          <div key={s.n} className="on-scroll group relative bg-card/25 p-8 transition-colors hover:bg-card/50" style={{ transitionDelay: `${i * 60}ms` }}>
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-light text-foreground/90">{s.t}</span>
              <span className="text-xs tabular text-violet/80">{s.n}</span>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
            <span className="mt-6 block h-px w-full origin-left scale-x-0 bg-gradient-to-r from-violet via-cyan to-transparent transition-transform duration-500 group-hover:scale-x-100" />
          </div>
        ))}
      </div>
    </section>
  );
}

/* Chain-agnostic: text left, technical architecture diagram (SVG) right. */
function MultiChain() {
  const bullets: [string, string][] = [
    ["Issue where your investors are", "Launch the same asset on the network your buyers and partners already use — the KYC/OFAC and lifecycle logic is identical on every chain."],
    ["No lock-in, no rebuild", "Move to or add a chain without re-engineering; your operations, reporting and audit trail stay exactly the same."],
    ["One USDC settlement rail", "Coupons and principal paid in Circle USDC on every network, from one workflow."],
  ];
  return (
    <section id="chains" className="border-y border-border/50 bg-card/15 py-28">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-6 lg:grid-cols-[0.82fr_1.18fr]">
        <div className="on-scroll">
          <p className="text-[11px] uppercase tracking-[0.3em] text-cyan">Reach investors on any chain</p>
          <h2 className="mt-5 text-5xl font-extralight leading-[1.05] sm:text-6xl">
            One engine.
            <br />
            <span className="text-iris font-light">Every network.</span>
          </h2>
          <p className="mt-7 text-lg leading-relaxed text-muted-foreground">
            Your investors and partners aren&apos;t all on one chain — and you shouldn&apos;t have to
            rebuild for each. Lamina issues and services the same compliant asset on whichever network
            you choose, with one workflow and one audit trail, settling in USDC everywhere.
          </p>
          <ul className="mt-8 space-y-4">
            {bullets.map(([t, d]) => (
              <li key={t} className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan shadow-[0_0_8px_hsl(var(--cyan))]" />
                <span className="text-sm leading-relaxed">
                  <span className="text-foreground">{t}.</span>{" "}
                  <span className="text-muted-foreground">{d}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <ArchitectureSVG />
      </div>
    </section>
  );
}

function ArchitectureSVG() {
  const evm = CHAINS.filter((c) => c.family === "evm");
  const hedera = CHAINS.filter((c) => c.family === "hedera")[0];

  // Excalidraw-style monochrome "pen" — colour comes only from the logos.
  const PEN = "hsl(233 14% 70%)";
  const TXT = "hsl(233 22% 90%)";
  const MUT = "hsl(235 10% 58%)";
  const FONT = '"Hanken Grotesk", ui-sans-serif, system-ui, sans-serif';

  const interfaces = [
    { logo: "/logo.svg", t: "REST · Web", s: "operator console" },
    { logo: "/chains/telegram.png", t: "Telegram", s: "natural language" },
    { logo: "/chains/mcp.png", t: "MCP server", s: "agent-to-agent" },
  ];
  const modules = [
    ["Issuance", "ERC-3643 deploy"],
    ["Compliance", "KYC · OFAC SDN"],
    ["Lifecycle", "coupons · NAV · maturity"],
    ["Reporting", "PDF · audit trail"],
  ];

  // clean straight arrowhead (open chevron), tip at (x,y) pointing right
  const head = (x: number, y: number) => `M${x - 11} ${y - 7} L${x} ${y} L${x - 11} ${y + 7}`;
  const MID = 257; // arrow height — vertical middle of the interface frame

  return (
    <div className="on-scroll">
      <svg viewBox="0 0 960 520" className="w-full" style={{ fontFamily: FONT }}>
        {/* ─── frames + boxes ─── */}
        <g fill="none" strokeLinejoin="round">
          {/* group frames */}
          <g stroke={PEN} strokeOpacity="0.45" strokeWidth="1.4">
            <rect x="40" y="70" width="220" height="374" rx="10" />
            <rect x="370" y="70" width="220" height="424" rx="10" />
            <rect x="700" y="70" width="220" height="356" rx="10" />
          </g>
          {/* inner boxes */}
          <g stroke={PEN} strokeOpacity="0.7" strokeWidth="1.3">
            {interfaces.map((_, i) => (
              <rect key={i} x="60" y={96 + i * 116} width="180" height="90" rx="7" />
            ))}
            {modules.map((_, i) => (
              <rect key={i} x="390" y={116 + i * 94} width="180" height="72" rx="7" />
            ))}
            <rect x="720" y="96" width="180" height="170" rx="7" />
            <rect x="720" y="290" width="180" height="110" rx="7" />
          </g>
          {/* straight arrows */}
          <g stroke={PEN} strokeOpacity="0.8" strokeWidth="1.6" strokeLinecap="round">
            <line x1="260" y1={MID} x2="366" y2={MID} />
            <path d={head(368, MID)} />
            <line x1="590" y1={MID} x2="696" y2={MID} />
            <path d={head(698, MID)} />
          </g>
        </g>

        {/* ─── labels + logos ─── */}
        {/* group titles */}
        <text x="40" y="52" fill={TXT} fontSize="19">Interfaces</text>
        <text x="370" y="52" fill={TXT} fontSize="19">Lamina engine</text>
        <text x="700" y="52" fill={TXT} fontSize="19">Networks · USDC</text>

        {/* interfaces */}
        {interfaces.map((it, i) => {
          const y = 96 + i * 116;
          return (
            <g key={it.t}>
              <image href={`${it.logo}?v=6`} x="78" y={y + 27} width="36" height="36" />
              <text x="126" y={y + 40} fill={TXT} fontSize="16">{it.t}</text>
              <text x="126" y={y + 60} fill={MUT} fontSize="13">{it.s}</text>
            </g>
          );
        })}

        {/* engine */}
        <text x="480" y="100" fill={MUT} fontSize="13" textAnchor="middle">AI agent · Claude · Postgres</text>
        {modules.map(([t, s], i) => {
          const y = 116 + i * 94;
          return (
            <g key={t}>
              <text x="480" y={y + 30} fill={TXT} fontSize="16" textAnchor="middle">{t}</text>
              <text x="480" y={y + 50} fill={MUT} fontSize="13" textAnchor="middle">{s}</text>
            </g>
          );
        })}

        {/* networks */}
        <text x="810" y="122" fill={MUT} fontSize="13" textAnchor="middle">EVM · ERC-3643</text>
        {evm.map((c, i) => {
          const col = i % 4;
          const row = Math.floor(i / 4);
          return (
            <image key={c.slug} href={`${c.logo}?v=6`} x={730 + col * 42} y={146 + row * 56} width="38" height="38">
              <title>{c.name}</title>
            </image>
          );
        })}
        <text x="810" y="318" fill={MUT} fontSize="13" textAnchor="middle">Hedera · HTS / HCS</text>
        {hedera && <image href={`${hedera.logo}?v=6`} x="786" y="336" width="48" height="48" />}

        {/* arrow labels */}
        <text x="313" y={MID - 12} fill={MUT} fontSize="13" textAnchor="middle">commands</text>
        <text x="644" y={MID - 12} fill={MUT} fontSize="13" textAnchor="middle">deploy · settle</text>
      </svg>
    </div>
  );
}

function Surfaces() {
  const s = [
    { logo: "/logo.svg", t: "REST & web console", d: "Issue, onboard, distribute, and settle from a typed API and the operator dashboard." },
    { logo: "/chains/telegram.png", t: "Telegram Bot API", d: "Operate the lifecycle in natural language, with an explicit confirmation step before any state-changing call." },
    { logo: "/chains/mcp.png", t: "Model Context Protocol", d: "An authenticated, scope-gated MCP server lets other agents and back-office systems drive Lamina." },
  ];
  return (
    <section id="surfaces" className="mx-auto max-w-7xl px-6 py-28">
      <SectionHead eyebrow="Integrations" title="Operated by people and agents." />
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {s.map((x, i) => (
          <div key={i} className="on-scroll rounded-2xl border border-border/50 bg-card/25 p-8" style={{ transitionDelay: `${i * 80}ms` }}>
            <div className="mb-5 grid h-11 w-11 place-items-center rounded-xl border border-border/70 bg-background">
              <img src={`${x.logo}?v=6`} alt="" className="h-6 w-6 object-contain" />
            </div>
            <h3 className="text-xl font-light">{x.t}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{x.d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Trust() {
  const items: [string, string][] = [
    ["Permissioned transfers", "ERC-3643 (T-REX) on EVM networks; native Hedera Token Service KYC, freeze and wipe keys on Hedera — the correct primitive on each chain."],
    ["OFAC SDN screening", "Investor names and digital-currency addresses checked against the U.S. Treasury Specially Designated Nationals list before any whitelist or transfer."],
    ["Immutable audit trail", "Access-controlled on-chain AuditLog on EVM; Hedera Consensus Service (HCS) on Hedera. Every agent action is recorded on the network it ran on."],
    ["Verified & tested", "Contracts source-verified on each network's block explorer; a 19-case Foundry suite covers compliance gating and access control."],
  ];
  return (
    <section id="trust" className="border-y border-border/50 bg-card/15 py-28">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHead eyebrow="Compliance & assurance" title="The right standard on every chain." />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {items.map(([t, d], i) => (
            <div key={t} className="on-scroll rounded-2xl border border-border/50 bg-background p-6" style={{ transitionDelay: `${i * 60}ms` }}>
              <h3 className="text-sm font-medium text-violet">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{d}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="relative mx-auto max-w-7xl px-6 py-32 text-center">
      <div className="aura aura-violet left-1/2 top-1/2 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2" />
      <h2 className="relative text-5xl font-extralight leading-tight sm:text-6xl">
        Issuance is solved.
        <br />
        <span className="text-iris font-light">Lifecycle operations</span> are not.
      </h2>
      <p className="relative mx-auto mt-6 max-w-xl text-muted-foreground">
        Hand the operating burden to the agent. Issue your first ERC-3643 asset in a single instruction.
      </p>
      <div className="relative mt-9 flex justify-center gap-3">
        <Link href="/dashboard" className="rounded-full bg-primary px-7 py-3.5 text-sm font-medium text-primary-foreground transition-all hover:shadow-[0_0_34px_hsl(var(--violet)/0.5)]">
          Launch the agent →
        </Link>
        <Link href="/chat" className="rounded-full border border-border bg-card/40 px-7 py-3.5 text-sm transition-colors hover:border-cyan/40">
          Open the console
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  const cols: [string, string[]][] = [
    ["Platform", ["Lifecycle", "Networks", "Integrations", "Compliance"]],
    ["Developers", ["Contracts on Arbiscan", "MCP server", "REST API", "Audit trail"]],
    ["Standards", ["ERC-3643 · ERC-20", "Hedera HTS / HCS", "OFAC SDN", "Reg D · Reg S"]],
  ];
  return (
    <footer className="border-t border-border/50 bg-ink-1/40">
      <div className="mx-auto grid max-w-7xl gap-10 px-6 py-14 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <div className="flex items-center gap-2.5">
            <Logo />
            <span className="text-lg font-medium">Lamina</span>
          </div>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
            The autonomous lifecycle layer for tokenized real-world assets. Compliant by construction,
            across every network.
          </p>
        </div>
        {cols.map(([h, items]) => (
          <div key={h}>
            <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground/70">{h}</div>
            <ul className="mt-4 space-y-2.5 text-sm text-muted-foreground">
              {items.map((it) => (
                <li key={it} className="transition-colors hover:text-foreground">{it}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border/40">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-6 py-6 text-xs text-muted-foreground/70 sm:flex-row">
          <span>© {new Date().getFullYear()} Lamina. Autonomous RWA lifecycle infrastructure.</span>
          <span>EVM · Hedera · Arbitrum Orbit</span>
        </div>
      </div>
    </footer>
  );
}

function SectionHead({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div className="on-scroll max-w-2xl">
      <p className="text-[11px] uppercase tracking-[0.3em] text-cyan">{eyebrow}</p>
      <h2 className="mt-4 text-4xl font-extralight leading-tight sm:text-5xl">{title}</h2>
      {sub && <p className="mt-4 text-muted-foreground">{sub}</p>}
    </div>
  );
}
