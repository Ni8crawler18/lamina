"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

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
      <div className="text-sm text-muted-foreground text-center py-8">
        No holders registered
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Account</TableHead>
          <TableHead className="text-right">Balance</TableHead>
          <TableHead>KYC</TableHead>
          <TableHead>Jurisdiction</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Whitelisted</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {holders.map((h) => (
          <TableRow key={h.id}>
            <TableCell className="font-mono text-xs">{h.account_id}</TableCell>
            <TableCell className="text-right font-semibold">
              {(h.balance / Math.pow(10, decimals)).toLocaleString()}
            </TableCell>
            <TableCell>
              <Badge
                variant="outline"
                className={
                  h.kyc_status === "approved"
                    ? "bg-green-500/10 text-green-500 border-green-500/20"
                    : "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
                }
              >
                {h.kyc_status}
              </Badge>
            </TableCell>
            <TableCell>{h.jurisdiction}</TableCell>
            <TableCell className="text-xs">{h.investor_type}</TableCell>
            <TableCell>
              {h.whitelisted ? (
                <span className="text-green-500">Yes</span>
              ) : (
                <span className="text-red-500">No</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
