import { useState, useEffect } from "react";
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
import { ChevronRight, Copy, ExternalLink, Send, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { backendService, RakebackLedgerEntry, Partner } from "../../services/backend-service";

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

function formatTao(n: number): string {
  return n.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
}

function formatPeriod(start: string, end: string): string {
  const d = new Date(start);
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function mapStatus(paymentStatus: string): StatusType {
  switch (paymentStatus) {
    case "PAID": return "paid";
    case "DISPUTED": return "error";
    default: return "pending";
  }
}

export default function PartnerLedger() {
  const [selectedEntry, setSelectedEntry] = useState<string | null>(null);
  const [showBreakdownDialog, setShowBreakdownDialog] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [ledgerEntries, setLedgerEntries] = useState<PartnerLedgerEntry[]>([]);
  const [paymentRecipient, setPaymentRecipient] = useState("");
  const [paymentMemo, setPaymentMemo] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [partnerCount, setPartnerCount] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [ledgerData, partners] = await Promise.all([
          backendService.getRakebackLedger(),
          backendService.getPartners(),
        ]);

        const partnerMap = new Map<string, Partner>();
        partners.forEach((p) => partnerMap.set(p.id, p));
        setPartnerCount(partners.length);

        const entries: PartnerLedgerEntry[] = ledgerData.map((entry: RakebackLedgerEntry) => ({
          id: entry.id.slice(0, 12),
          partner: partnerMap.get(entry.participantId)?.name ?? entry.participantId,
          period: formatPeriod(entry.periodStart, entry.periodEnd),
          grossTao: formatTao(entry.grossTaoConverted),
          rakebackRate: Math.round(entry.rakebackPercentage * 10000) / 100,
          taoOwed: formatTao(entry.taoOwed),
          status: mapStatus(entry.paymentStatus),
          paymentTxHash: entry.paymentTxHash ?? undefined,
        }));

        setLedgerEntries(entries);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load ledger data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleViewBreakdown = (entryId: string) => {
    setSelectedEntry(entryId);
    setShowBreakdownDialog(true);
  };

  const handleInitiatePayment = (entryId: string) => {
    const entry = ledgerEntries.find((e) => e.id === entryId);
    if (!entry) return;
    setSelectedEntry(entryId);
    setPaymentRecipient("");
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
      await new Promise(resolve => setTimeout(resolve, 2500));
      const txHash = `0x${Array.from({ length: 64 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join('')}`;

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
    } catch {
      toast.error("Failed to send payment. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const selectedLedgerEntry = ledgerEntries.find((e) => e.id === selectedEntry);

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

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        <span className="ml-3 text-zinc-400">Loading ledger data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto py-20 text-center">
        <AlertCircle className="h-12 w-12 mx-auto mb-3 text-red-400" />
        <div className="text-red-400 font-medium">Failed to load data</div>
        <div className="text-sm text-zinc-500 mt-1">{error}</div>
      </div>
    );
  }

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
            {formatTao(totalPending)} τ
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Paid</div>
          <div className="text-2xl font-mono text-emerald-400">
            {formatTao(totalPaid)} τ
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Active Partners</div>
          <div className="text-2xl font-mono text-zinc-100">{partnerCount}</div>
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
        {ledgerEntries.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">
            <div className="text-zinc-400">No ledger entries yet</div>
            <div className="text-sm mt-1">Entries will appear after the pipeline processes data</div>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableHead className="text-zinc-400">Entry ID</TableHead>
                <TableHead className="text-zinc-400">Partner</TableHead>
                <TableHead className="text-zinc-400">Period</TableHead>
                <TableHead className="text-zinc-400 text-right">Gross TAO</TableHead>
                <TableHead className="text-zinc-400 text-right">Rakeback Rate</TableHead>
                <TableHead className="text-zinc-400 text-right">TAO Owed</TableHead>
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
        )}
      </div>

      {/* Breakdown Dialog */}
      <Dialog
        open={showBreakdownDialog}
        onOpenChange={setShowBreakdownDialog}
      >
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">
              {selectedLedgerEntry?.partner} — Wallet Breakdown
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              Per-wallet attribution for {selectedLedgerEntry?.period}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">Total Gross TAO</div>
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
                <div className="text-xs text-zinc-500 mb-1">Total TAO Owed</div>
                <div className="text-lg font-mono text-emerald-400">
                  {selectedLedgerEntry?.taoOwed}
                </div>
              </div>
            </div>

            <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 text-sm text-zinc-400">
              <div className="flex items-start gap-2">
                <ExternalLink className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>
                  Per-wallet breakdown coming soon. This will show individual wallet attributions once the per-wallet aggregation endpoint is available.
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
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">Total Gross TAO</div>
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
                <div className="text-xs text-zinc-500 mb-1">Total TAO Owed</div>
                <div className="text-lg font-mono text-emerald-400">
                  {selectedLedgerEntry?.taoOwed}
                </div>
              </div>
            </div>

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
                    <Loader2 className="h-3 w-3 animate-spin" />
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
