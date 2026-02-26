const BADGES = [
  { label: "SEC Reg D", description: "US accredited investors" },
  { label: "SEC Reg S", description: "Non-US offerings" },
  { label: "MiFID II", description: "EU financial instruments" },
  { label: "ERC-1400", description: "Security token standard" },
  { label: "ERC-3643", description: "Identity-based tokens" },
  { label: "OFAC", description: "Sanctions screening" },
];

export default function Regulatory() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto text-center">
        <p className="text-xs font-medium text-primary uppercase tracking-wider mb-3">Compliance</p>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
          Pre-configured for major jurisdictions
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto mb-12">
          Every asset is deployed with the right regulatory framework. Compliance rules are
          enforced on every transfer — automatically.
        </p>

        <div className="flex flex-wrap justify-center gap-3">
          {BADGES.map((badge) => (
            <div
              key={badge.label}
              className="flex flex-col items-center px-6 py-4 rounded-xl border border-border/50 bg-card/30 hover:border-primary/20 transition-colors min-w-[140px]"
            >
              <span className="text-sm font-semibold mb-1">{badge.label}</span>
              <span className="text-[11px] text-muted-foreground">{badge.description}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
