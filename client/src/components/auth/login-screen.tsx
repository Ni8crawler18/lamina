"use client";

import { useEffect, useState } from "react";
import { useWallet } from "@/contexts/wallet-context";
import { Zap } from "lucide-react";

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground" />;
}

function GoogleG() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

export default function LoginScreen() {
  const { connectMetaMask, connectHashPack, connectPhantom, connectGoogle, connectDemo, isConnecting, error } = useWallet();
  const [pending, setPending] = useState<string | null>(null);

  // clear the per-button spinner when the global connecting flag settles
  useEffect(() => { if (!isConnecting) setPending(null); }, [isConnecting]);

  const run = (key: string, fn: () => void) => { setPending(key); fn(); };

  const Row = ({
    pkey, onClick, icon, label, sub, primary,
  }: { pkey: string; onClick: () => void; icon: React.ReactNode; label: string; sub: string; primary?: boolean }) => (
    <button
      onClick={() => run(pkey, onClick)}
      disabled={isConnecting}
      className={`group flex w-full items-center gap-3.5 rounded-xl border px-4 py-3.5 text-left transition-all disabled:opacity-50 ${
        primary
          ? "border-violet/40 bg-violet/[0.08] hover:bg-violet/[0.14]"
          : "border-border/60 bg-card/40 hover:border-border hover:bg-card/70"
      }`}
    >
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-border/60 bg-background">{icon}</span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-foreground">{label}</span>
        <span className="block text-xs text-muted-foreground">{sub}</span>
      </span>
      <span className="ml-auto shrink-0">
        {pending === pkey ? (
          <Spinner />
        ) : (
          <svg className="h-4 w-4 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18l6-6-6-6" />
          </svg>
        )}
      </span>
    </button>
  );

  return (
    <div className="relative flex min-h-screen flex-col overflow-y-auto bg-background">
      {/* grid + aura are masked background layers — kept separate so they don't mask the card */}
      <div className="pointer-events-none absolute inset-0 bg-vault-grid" />
      <div className="aura aura-violet left-1/2 top-[-120px] h-[420px] w-[680px] -translate-x-1/2" />
      <div className="relative z-10 mx-auto my-auto w-full max-w-md px-6 py-12">
        <div className="w-full">
          <div className="mb-8 flex items-center justify-center gap-2.5">
            <img src="/logo.svg" alt="Lamina" className="h-8 w-8" />
            <span className="text-xl font-medium tracking-tight">Lamina</span>
          </div>

          <div className="glass rounded-2xl p-7">
            <h1 className="text-lg font-semibold">Sign in to operate</h1>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Connect to issue and manage tokenized assets across every network. Choose how you&apos;d like to sign in.
            </p>

            <div className="mt-6 space-y-2.5">
              <Row pkey="mm" onClick={connectMetaMask} primary icon={<img src="/chains/metamask.png" alt="" className="h-6 w-6 object-contain" />} label="MetaMask" sub="EVM networks · browser wallet" />
              <Row pkey="hp" onClick={connectHashPack} icon={<img src="/chains/hedera.png?v=6" alt="" className="h-5 w-5 object-contain" />} label="HashPack" sub="Hedera · HTS / HCS" />
              <Row pkey="ph" onClick={connectPhantom} icon={<img src="/chains/solana.png" alt="" className="h-6 w-6 object-contain" />} label="Phantom" sub="Solana · Token-2022" />
              <Row pkey="g" onClick={connectGoogle} icon={<GoogleG />} label="Continue with Google" sub="Operator identity · no wallet needed" />
            </div>

            <div className="my-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-border/50" />
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">or</span>
              <div className="h-px flex-1 bg-border/50" />
            </div>

            <button
              onClick={() => run("demo", connectDemo)}
              disabled={isConnecting}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-border/50 px-4 py-3 text-sm font-medium text-muted-foreground transition-all hover:border-border hover:text-foreground disabled:opacity-50"
            >
              {pending === "demo" ? <Spinner /> : <Zap className="h-4 w-4" />}
              {pending === "demo" ? "Connecting…" : "Explore in demo mode"}
            </button>

            {error && (
              <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </p>
            )}
          </div>

          <p className="mt-6 text-center text-[11px] leading-relaxed text-muted-foreground/70">
            Lamina&apos;s agent signs on-chain actions; your wallet identifies you and your investors.
            Testnet only — no mainnet funds at risk.
          </p>
        </div>
      </div>
    </div>
  );
}
