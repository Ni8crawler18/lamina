import { Coins, ShieldCheck, RefreshCw, CheckCircle2 } from "lucide-react";

const STEPS = [
  {
    icon: Coins,
    title: "Issue",
    description: "Deploy compliant security tokens on Hedera with built-in regulatory framework",
  },
  {
    icon: ShieldCheck,
    title: "Comply",
    description: "Automated KYC whitelist, transfer restrictions, and jurisdiction enforcement",
  },
  {
    icon: RefreshCw,
    title: "Manage",
    description: "Autonomous coupon payments, NAV updates, and investor communications",
  },
  {
    icon: CheckCircle2,
    title: "Settle",
    description: "Maturity redemption — return principal, burn tokens, generate final reports",
  },
];

export default function HowItWorks() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-xs font-medium text-primary uppercase tracking-wider mb-3">How It Works</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Full lifecycle in four steps
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-10 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-transparent via-border to-transparent" />

          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={i} className="text-center relative">
                <div className="w-20 h-20 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5 relative z-10">
                  <Icon className="w-8 h-8 text-primary" strokeWidth={1.5} />
                </div>
                <div className="absolute top-2 right-0 text-[64px] font-bold text-muted/30 leading-none select-none -z-0 hidden md:block">
                  {i + 1}
                </div>
                <h3 className="text-base font-semibold mb-2">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
