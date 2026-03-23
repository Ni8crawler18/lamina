import Link from "next/link";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background orb */}
      <div className="gradient-orb top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />

      <div className="relative z-10 max-w-4xl mx-auto text-center px-6">
        {/* Badge */}
        <div className="animate-fade-in-up">
          <span className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary mb-8">
            <svg width="14" height="14" viewBox="0 0 28 28" fill="none">
              <path d="M14 22L4 16.5L14 11L24 16.5L14 22Z" fill="#5a3db5" opacity="0.6"/>
              <path d="M14 18L4 12.5L14 7L24 12.5L14 18Z" fill="#7c5ce7" opacity="0.8"/>
              <path d="M14 14L4 8.5L14 3L24 8.5L14 14Z" fill="#a78bfa"/>
            </svg>
            Built on Hedera
          </span>
        </div>

        {/* Heading */}
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6 animate-fade-in-up-delay-1">
          Autonomous RWA<br />
          <span className="text-gradient">Lifecycle Management</span>
        </h1>

        {/* Subtitle */}
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in-up-delay-2">
          From issuance to maturity. Tokenize bonds, manage compliance,
          distribute coupons — all powered by AI on Hedera.
        </p>

        {/* CTAs */}
        <div className="flex items-center justify-center gap-4 animate-fade-in-up-delay-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/90 px-6 py-3 rounded-xl transition-colors glow-purple"
          >
            Launch App
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
          <Link
            href="/slides.html"
            target="_blank"
            className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground border border-border/50 hover:border-border px-6 py-3 rounded-xl transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h16.5M3.75 3l3 9m13.5-9v11.25A2.25 2.25 0 0118 16.5h-2.25m0 0L12 21m3.75-4.5L12 21m0 0l-3.75-4.5" />
            </svg>
            Pitch Deck
          </Link>
          <a
            href="https://github.com/Ni8crawler18/lamina"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground border border-border/50 hover:border-border px-6 py-3 rounded-xl transition-all"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            GitHub
          </a>
        </div>
      </div>
    </section>
  );
}
