import { useState } from "react";
import { StatusBadge, StatusType } from "../components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { ChevronRight, Copy, ExternalLink, Send, AlertCircle } from "lucide-react";
import { toast } from "sonner";

interface PartnerLedgerEntry {
  id: string;
  partner: string;
  period: string;
  grossTao: string;
  rakebackRate: number;
  taoOwed: string;
  status: StatusType;
  paymentTxHash?: string;
}

const mockLedger: PartnerLedgerEntry[] = [
  {
    id: "PL-CB-2026-02",
    partner: "Creative Builds",
    period: "February 2026",
    grossTao: "8,432.5821",
    rakebackRate: 15,
    taoOwed: "1,264.8873",
    status: "pending",
  },
  {
    id: "PL-TL-2026-02",
    partner: "Talisman",
    period: "February 2026",
    grossTao: "3,241.9023",
    rakebackRate: 12,
    taoOwed: "388.9283",
    status: "pending",
  },
  {
    id: "PL-CB-2026-01",
    partner: "Creative Builds",
    period: "January 2026",
    grossTao: "12,567.3492",
    rakebackRate: 15,
    taoOwed: "1,885.1024",
    status: "paid",
    paymentTxHash:
      "0x8f3d9e2a1b4c6f7e8d9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e",
  },
  {
    id: "PL-TL-2026-01",
    partner: "Talisman",
    period: "January 2026",
    grossTao: "4,893.2014",
    rakebackRate: 12,
    taoOwed: "587.1842",
    status: "paid",
    paymentTxHash:
      "0x7e2c8d1a9b0f3e4d5c6a7b8e9f0d1c2b3a4e5f6d7c8a9b0e1f2d3c4a5b6e7f8d",
  },
  {
    id: "PL-CB-2025-12",
    partner: "Creative Builds",
    period: "December 2025",
    grossTao: "11,234.8923",
    rakebackRate: 15,
    taoOwed: "1,685.2338",
    status: "paid",
    paymentTxHash:
      "0x6d1f9e0a8b7c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e",
  },
  {
    id: "PL-TL-2025-12",
    partner: "Talisman",
    period: "December 2025",
    grossTao: "5,102.4782",
    rakebackRate: 12,
    taoOwed: "612.2974",
    status: "paid",
    paymentTxHash:
      "0x5c0e8d9a7b6f4e3d2c1a0b9f8e7d6c5a4b3e2d1f0c9a8b7e6d5f4c3a2b1e0d9f",
  },
];

interface WalletBreakdown {
  wallet: string;
  grossTao: string;
  rakebackTao: string;
  stakeCount: number;
}

const mockCreativeBuildsBreakdown: WalletBreakdown[] = [
  {
    wallet: "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL",
    grossTao: "8,432.5821",
    rakebackTao: "1,264.8873",
    stakeCount: 1,
  },
];

const mockTalismanBreakdown: WalletBreakdown[] = [
  {
    wallet: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    grossTao: "1,823.4521",
    rakebackTao: "218.8142",
    stakeCount: 1,
  },
  {
    wallet: "5DfhGyQdFobKM8NsWvEeAKk5EQQgYe9AydgJ7rMB6E1EqRzV",
    grossTao: "1,418.4502",
    rakebackTao: "170.1140",
    stakeCount: 1,
  },
];

export default function PartnerLedger() {
  const [selectedEntry, setSelectedEntry] = useState<string | null>(null);
  const [showBreakdownDialog, setShowBreakdownDialog] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [ledgerEntries, setLedgerEntries] = useState<PartnerLedgerEntry[]>(mockLedger);
  const [paymentRecipient, setPaymentRecipient] = useState("");
  const [paymentMemo, setPaymentMemo] = useState("");
  const [isSending, setIsSending] = useState(false);

  const handleViewBreakdown = (entryId: string) => {
    setSelectedEntry(entryId);
    setShowBreakdownDialog(true);
  };

  const handleInitiatePayment = (entryId: string) => {
    const entry = ledgerEntries.find((e) => e.id === entryId);
    if (!entry) return;
    
    setSelectedEntry(entryId);
    
    // Pre-fill recipient based on partner
    const breakdown = entry.partner === "Creative Builds" 
      ? mockCreativeBuildsBreakdown 
      : mockTalismanBreakdown;
    
    if (breakdown.length === 1) {
      setPaymentRecipient(breakdown[0].wallet);
    } else {
      setPaymentRecipient(""); // Multi-wallet, user must choose
    }
    
    setPaymentMemo(`Rakeback payment - ${entry.partner} - ${entry.period}`);
    setShowPaymentDialog(true);
  };

  const handleSendPayment = async () => {
    if (!selectedEntry || !paymentRecipient) {
      toast.error("Please fill in all required fields");
      return;
    }

    const entry = ledgerEntries.find((e) => e.id === selectedEntry);
    if (!entry) return;

    setIsSending(true);

    try {
      // Simulate transaction sending (2-3 seconds)
      await new Promise(resolve => setTimeout(resolve, 2500));
      
      // Generate mock transaction hash
      const txHash = `0x${Array.from({ length: 64 }, () => 
        Math.floor(Math.random() * 16).toString(16)
      ).join('')}`;

      // Update ledger entry
      setLedgerEntries(prev => prev.map(e => 
        e.id === selectedEntry 
          ? { ...e, status: "paid" as StatusType, paymentTxHash: txHash }
          : e
      ));

      toast.success(
        <div>
          <div className="font-medium">Payment sent successfully!</div>
          <div className="text-xs text-zinc-400 mt-1 font-mono">
            Tx: {txHash.slice(0, 10)}...{txHash.slice(-8)}
          </div>
        </div>
      );

      setShowPaymentDialog(false);
      setPaymentRecipient("");
      setPaymentMemo("");
    } catch (error) {
      toast.error("Failed to send payment. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const selectedLedgerEntry = ledgerEntries.find((e) => e.id === selectedEntry);
  const breakdownData =
    selectedLedgerEntry?.partner === "Creative Builds"
      ? mockCreativeBuildsBreakdown
      : mockTalismanBreakdown;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const totalPending = ledgerEntries
    .filter((e) => e.status === "pending")
    .reduce((acc, e) => acc + parseFloat(e.taoOwed.replace(/,/g, "")), 0);

  const totalPaid = ledgerEntries
    .filter((e) => e.status === "paid")
    .reduce((acc, e) => acc + parseFloat(e.taoOwed.replace(/,/g, "")), 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Partner Rakeback Ledger
        </h2>
        <p className="text-sm text-zinc-400">
          Finance-grade tracking of partner attributions and payment obligations
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Entries</div>
          <div className="text-2xl font-mono text-zinc-100">
            {ledgerEntries.length}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Pending Payments</div>
          <div className="text-2xl font-mono text-amber-400">
            {totalPending.toFixed(4)} τ
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Paid</div>
          <div className="text-2xl font-mono text-emerald-400">
            {totalPaid.toFixed(4)} τ
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Active Partners</div>
          <div className="text-2xl font-mono text-zinc-100">2</div>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h3 className="font-medium text-zinc-50">Ledger Entries</h3>
          <p className="text-sm text-zinc-400 mt-1">
            Monthly rakeback calculations and payment status
          </p>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Entry ID</TableHead>
              <TableHead className="text-zinc-400">Partner</TableHead>
              <TableHead className="text-zinc-400">Period</TableHead>
              <TableHead className="text-zinc-400 text-right">
                Gross TAO
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Rakeback Rate
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                TAO Owed
              </TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
              <TableHead className="text-zinc-400">Payment Tx</TableHead>
              <TableHead className="text-zinc-400">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ledgerEntries.map((entry) => (
              <TableRow
                key={entry.id}
                className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
              >
                <TableCell className="font-mono text-sm text-zinc-300">
                  {entry.id}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2.5 py-1 rounded text-sm font-medium bg-zinc-800 text-zinc-100 border border-zinc-700">
                    {entry.partner}
                  </span>
                </TableCell>
                <TableCell className="text-zinc-400">{entry.period}</TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {entry.grossTao}
                </TableCell>
                <TableCell className="text-right text-zinc-400">
                  {entry.rakebackRate}%
                </TableCell>
                <TableCell className="text-right font-mono text-emerald-400">
                  {entry.taoOwed}
                </TableCell>
                <TableCell>
                  <StatusBadge status={entry.status} />
                </TableCell>
                <TableCell>
                  {entry.paymentTxHash ? (
                    <button
                      onClick={() => copyToClipboard(entry.paymentTxHash!)}
                      className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      <span>
                        {entry.paymentTxHash.slice(0, 6)}...
                        {entry.paymentTxHash.slice(-4)}
                      </span>
                      <Copy className="h-3 w-3" />
                    </button>
                  ) : (
                    <span className="text-xs text-zinc-600">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {entry.status === "pending" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleInitiatePayment(entry.id)}
                        className="bg-emerald-900/20 border-emerald-800 text-emerald-400 hover:bg-emerald-900/40 hover:text-emerald-300"
                      >
                        <Send className="h-3 w-3 mr-1.5" />
                        Send
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewBreakdown(entry.id)}
                      className="text-zinc-400 hover:text-zinc-200"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Breakdown Dialog */}
      <Dialog
        open={showBreakdownDialog}
        onOpenChange={setShowBreakdownDialog}
      >
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">
              {selectedLedgerEntry?.partner} Wallet Breakdown
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              Per-wallet attribution for {selectedLedgerEntry?.period}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Total Gross TAO
                </div>
                <div className="text-lg font-mono text-zinc-100">
                  {selectedLedgerEntry?.grossTao}
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">Rakeback Rate</div>
                <div className="text-lg font-mono text-zinc-100">
                  {selectedLedgerEntry?.rakebackRate}%
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Total TAO Owed
                </div>
                <div className="text-lg font-mono text-emerald-400">
                  {selectedLedgerEntry?.taoOwed}
                </div>
              </div>
            </div>

            {/* Wallet Table */}
            <div className="border border-zinc-800 rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                    <TableHead className="text-zinc-400">Wallet</TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Gross TAO
                    </TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Rakeback TAO
                    </TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Stake Count
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {breakdownData.map((wallet, idx) => (
                    <TableRow
                      key={idx}
                      className="border-zinc-800 hover:bg-zinc-800/50"
                    >
                      <TableCell className="font-mono text-xs text-zinc-300">
                        <div className="flex items-center gap-2">
                          {wallet.wallet.slice(0, 8)}...{wallet.wallet.slice(-8)}
                          <button
                            onClick={() => copyToClipboard(wallet.wallet)}
                            className="text-zinc-500 hover:text-zinc-300"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-zinc-100">
                        {wallet.grossTao}
                      </TableCell>
                      <TableCell className="text-right font-mono text-emerald-400">
                        {wallet.rakebackTao}
                      </TableCell>
                      <TableCell className="text-right text-zinc-400">
                        {wallet.stakeCount}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Note */}
            <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 text-sm text-zinc-400">
              <div className="flex items-start gap-2">
                <ExternalLink className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>
                  {selectedLedgerEntry?.partner === "Creative Builds"
                    ? "Creative Builds uses a single custody wallet. All TAO is aggregated to this address."
                    : "Talisman attribution is per-wallet based on extrinsic memo matching."}
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Payment Dialog */}
      <Dialog
        open={showPaymentDialog}
        onOpenChange={setShowPaymentDialog}
      >
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">
              Initiate Payment
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              Send TAO to the partner's wallet
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Total Gross TAO
                </div>
                <div className="text-lg font-mono text-zinc-100">
                  {selectedLedgerEntry?.grossTao}
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">Rakeback Rate</div>
                <div className="text-lg font-mono text-zinc-100">
                  {selectedLedgerEntry?.rakebackRate}%
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Total TAO Owed
                </div>
                <div className="text-lg font-mono text-emerald-400">
                  {selectedLedgerEntry?.taoOwed}
                </div>
              </div>
            </div>

            {/* Wallet Table */}
            <div className="border border-zinc-800 rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                    <TableHead className="text-zinc-400">Wallet</TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Gross TAO
                    </TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Rakeback TAO
                    </TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Stake Count
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {breakdownData.map((wallet, idx) => (
                    <TableRow
                      key={idx}
                      className="border-zinc-800 hover:bg-zinc-800/50"
                    >
                      <TableCell className="font-mono text-xs text-zinc-300">
                        <div className="flex items-center gap-2">
                          {wallet.wallet.slice(0, 8)}...{wallet.wallet.slice(-8)}
                          <button
                            onClick={() => copyToClipboard(wallet.wallet)}
                            className="text-zinc-500 hover:text-zinc-300"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-zinc-100">
                        {wallet.grossTao}
                      </TableCell>
                      <TableCell className="text-right font-mono text-emerald-400">
                        {wallet.rakebackTao}
                      </TableCell>
                      <TableCell className="text-right text-zinc-400">
                        {wallet.stakeCount}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Payment Form */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="recipient" className="text-zinc-300">Recipient Wallet</Label>
                <input
                  id="recipient"
                  value={paymentRecipient}
                  onChange={(e) => setPaymentRecipient(e.target.value)}
                  placeholder="Enter wallet address"
                  className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="memo" className="text-zinc-300">Payment Memo</Label>
                <input
                  id="memo"
                  value={paymentMemo}
                  onChange={(e) => setPaymentMemo(e.target.value)}
                  placeholder="Enter payment memo"
                  className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Send Button */}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPaymentDialog(false)}
                disabled={isSending}
                className="bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-zinc-100"
              >
                Cancel
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleSendPayment}
                disabled={isSending}
                className="bg-emerald-900/40 border border-emerald-800 text-emerald-400 hover:bg-emerald-900/60 hover:text-emerald-300"
              >
                {isSending ? (
                  <div className="flex items-center gap-1.5">
                    <AlertCircle className="h-3 w-3 animate-spin" />
                    Sending...
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <Send className="h-3 w-3" />
                    Send Payment
                  </div>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}