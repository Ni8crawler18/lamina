import {
  ShieldCheck,
  RefreshCw,
  ScrollText,
  TrendingUp,
  FileBarChart,
  MessageSquare,
} from "lucide-react";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Compliance Engine",
    description: "Pre-configured SEC Reg D, Reg S, MiFID II frameworks. Automated KYC whitelist and transfer restriction enforcement.",
  },
  {
    icon: RefreshCw,
    title: "Autonomous Lifecycle",
    description: "Scheduled coupon payments, maturity redemption, and token burns — all executed without human intervention.",
  },
  {
    icon: ScrollText,
    title: "Immutable Audit Trail",
    description: "Every agent action logged to Hedera Consensus Service. Cryptographically verifiable, tamper-proof records.",
  },
  {
    icon: TrendingUp,
    title: "Real-Time Valuation",
    description: "NAV updates from US Treasury yield curves and FX rate feeds. Automated mark-to-market on-chain.",
  },
  {
    icon: FileBarChart,
    title: "Regulatory Reporting",
    description: "Auto-generated compliance reports, investor statements, and audit summaries. Download-ready PDFs.",
  },
  {
    icon: MessageSquare,
    title: "Natural Language Control",
    description: "\"Tokenize a $10M bond\" — the AI agent interprets commands and orchestrates the full workflow.",
  },
];

export default function Features() {
  return (
    <section className="py-24 px-6 bg-card/30">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-xs font-medium text-primary uppercase tracking-wider mb-3">Features</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Everything an RWA needs, automated
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <div
                key={i}
                className="rounded-xl border border-border/50 bg-card/50 p-6 hover:border-primary/20 hover:bg-card/80 transition-all duration-200"
              >
                <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-primary" strokeWidth={1.5} />
                </div>
                <h3 className="text-sm font-semibold mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
