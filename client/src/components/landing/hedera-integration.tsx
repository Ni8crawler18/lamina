import { Coins, FileText, Globe } from "lucide-react";

const SERVICES = [
  {
    icon: Coins,
    name: "Hedera Token Service",
    abbr: "HTS",
    description: "Mint, transfer, and burn compliant security tokens. Distribute coupon payments as native HBAR transfers.",
    features: ["Token creation with compliance keys", "Proportional coupon distribution", "Maturity burn & redemption"],
  },
  {
    icon: FileText,
    name: "Hedera Consensus Service",
    abbr: "HCS",
    description: "Every agent action immutably logged. Cryptographic proof of compliance for regulators and auditors.",
    features: ["Per-asset audit topics", "Timestamped action logging", "Verifiable on HashScan"],
  },
  {
    icon: Globe,
    name: "Mirror Node API",
    abbr: "Mirror",
    description: "Query real-time token balances, transaction history, and HCS messages for dashboards and reports.",
    features: ["Holder balance queries", "Transaction verification", "HCS message retrieval"],
  },
];

export default function HederaIntegration() {
  return (
    <section className="py-24 px-6 bg-card/30">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-xs font-medium text-primary uppercase tracking-wider mb-3">Integration</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Deep Hedera integration
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto mt-4">
            Not a wrapper — Lamina uses Hedera&apos;s native services for every operation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SERVICES.map((service) => {
            const Icon = service.icon;
            return (
              <div
                key={service.abbr}
                className="rounded-xl border border-border/50 bg-background p-6 hover:border-primary/20 transition-colors"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-primary" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{service.name}</p>
                    <p className="text-[10px] text-muted-foreground font-mono">{service.abbr}</p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">{service.description}</p>
                <ul className="space-y-1.5">
                  {service.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="w-1 h-1 rounded-full bg-primary flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
