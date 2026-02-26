"use client";

interface Holder {
  id: number;
  account_id: string;
  balance: number;
  kyc_status: string;
  jurisdiction: string;
  investor_type: string;
  whitelisted: boolean | number;
}

export default function HolderTable({ holders, decimals = 2 }: { holders: Holder[]; decimals?: number }) {
  if (!holders || holders.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-12">
        No holders registered
      </p>
    );
  }

  return (
    <div className="overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="text-[11px] text-muted-foreground uppercase tracking-wider">
            <th className="text-left font-medium pb-3 pl-4">Account</th>
            <th className="text-right font-medium pb-3">Balance</th>
            <th className="text-left font-medium pb-3 pl-6">KYC</th>
            <th className="text-left font-medium pb-3">Jurisdiction</th>
            <th className="text-left font-medium pb-3">Type</th>
            <th className="text-center font-medium pb-3 pr-4">Whitelisted</th>
          </tr>
        </thead>
        <tbody>
          {holders.map((h) => (
            <tr key={h.id} className="border-t border-border/30 hover:bg-card/50 transition-colors">
              <td className="py-3 pl-4">
                <span className="font-mono text-xs">{h.account_id}</span>
              </td>
              <td className="py-3 text-right">
                <span className="font-mono text-sm font-medium">
                  {(h.balance / Math.pow(10, decimals)).toLocaleString()}
                </span>
              </td>
              <td className="py-3 pl-6">
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                  h.kyc_status === "approved"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-amber-500/10 text-amber-400"
                }`}>
                  {h.kyc_status}
                </span>
              </td>
              <td className="py-3 text-xs text-muted-foreground">{h.jurisdiction}</td>
              <td className="py-3 text-xs text-muted-foreground">{h.investor_type}</td>
              <td className="py-3 text-center pr-4">
                {h.whitelisted ? (
                  <svg className="w-4 h-4 text-emerald-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-red-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
