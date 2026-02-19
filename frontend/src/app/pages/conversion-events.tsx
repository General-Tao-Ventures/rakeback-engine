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
import { ChevronRight, TrendingUp, TrendingDown, Check, Loader2 } from "lucide-react";
import { useTaoPrice } from "../../hooks/use-tao-price";
import {
  backendService,
  type ConversionEvent,
  type ConversionDetail,
} from "../../services/backend-service";

export default function ConversionEvents() {
  const [conversions, setConversions] = useState<ConversionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [showAllocationDialog, setShowAllocationDialog] = useState(false);
  const [conversionDetail, setConversionDetail] = useState<ConversionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const {
    price: currentTaoPrice,
    change24h: priceChange24h,
    changePercent24h: priceChangePercent,
  } = useTaoPrice();

  useEffect(() => {
    setLoading(true);
    backendService
      .getConversions()
      .then(setConversions)
      .catch((err) => {
        console.error("Failed to fetch conversions:", err);
        setConversions([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleViewAllocation = async (eventId: string) => {
    setSelectedEventId(eventId);
    setShowAllocationDialog(true);
    setDetailLoading(true);
    setConversionDetail(null);

    try {
      const detail = await backendService.getConversionDetail(eventId);
      setConversionDetail(detail);
    } catch (err) {
      console.error("Failed to fetch conversion detail:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  const selectedConversion = conversions.find((c) => c.id === selectedEventId);

  // Compute summary stats from real data
  const totalDtaoSold = conversions.reduce(
    (acc, c) => acc + parseFloat(c.dtaoAmount),
    0
  );
  const totalTaoReceived = conversions.reduce(
    (acc, c) => acc + parseFloat(c.taoAmount),
    0
  );
  const avgRate =
    conversions.length > 0
      ? conversions.reduce((acc, c) => acc + parseFloat(c.conversionRate), 0) /
        conversions.length
      : 0;

  const getConversionStatus = (c: ConversionEvent): StatusType => {
    if (c.fullyAllocated) return "allocated";
    if (parseFloat(c.taoAmount) > 0) return "partial";
    return "unallocated";
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Conversion Events
        </h2>
        <p className="text-sm text-zinc-400">
          Transparent dTAO &rarr; TAO conversion tracking with pro-rata allocation to
          delegators
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Current TAO Price</div>
          <div className="text-2xl font-mono text-emerald-400">
            ${currentTaoPrice.toFixed(2)}
          </div>
          <div
            className={`flex items-center gap-1 mt-1.5 text-xs ${
              priceChangePercent >= 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {priceChangePercent >= 0 ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            <span className="font-medium">
              {priceChangePercent >= 0 ? "+" : ""}
              {priceChangePercent.toFixed(2)}%
            </span>
            <span className="text-zinc-500">24h</span>
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Conversions</div>
          <div className="text-2xl font-mono text-zinc-100">
            {conversions.length}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total dTAO Sold</div>
          <div className="text-2xl font-mono text-zinc-100">
            {totalDtaoSold.toLocaleString(undefined, {
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total TAO Received</div>
          <div className="text-2xl font-mono text-emerald-400">
            {totalTaoReceived.toLocaleString(undefined, {
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Avg Conversion Rate</div>
          <div className="text-2xl font-mono text-zinc-100">
            {avgRate.toFixed(4)}
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h3 className="font-medium text-zinc-50">Conversion Event Timeline</h3>
          <p className="text-sm text-zinc-400 mt-1">
            All conversion events with allocation status
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-zinc-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Loading conversions...
          </div>
        ) : conversions.length === 0 ? (
          <div className="text-center py-16 text-zinc-500">
            <p className="text-lg mb-1">No conversion events found</p>
            <p className="text-sm">
              Ingest conversion data first using the API, then events will appear
              here.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableHead className="text-zinc-400">Event ID</TableHead>
                <TableHead className="text-zinc-400">Block</TableHead>
                <TableHead className="text-zinc-400">Subnet</TableHead>
                <TableHead className="text-zinc-400 text-right">
                  dTAO Sold
                </TableHead>
                <TableHead className="text-zinc-400 text-right">
                  TAO Received
                </TableHead>
                <TableHead className="text-zinc-400 text-right">
                  Rate
                </TableHead>
                <TableHead className="text-zinc-400 text-right">
                  TAO Price
                </TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
                <TableHead className="text-zinc-400"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {conversions.map((event) => (
                <TableRow
                  key={event.id}
                  className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                >
                  <TableCell className="font-mono text-sm text-zinc-300">
                    {event.id.length > 12
                      ? event.id.slice(0, 8) + "..."
                      : event.id}
                  </TableCell>
                  <TableCell className="font-mono text-sm text-zinc-400">
                    {event.blockNumber.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {event.subnetId != null
                        ? event.subnetId === 0
                          ? "ROOT"
                          : `SN${event.subnetId}`
                        : "—"}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-zinc-100">
                    {parseFloat(event.dtaoAmount).toLocaleString(undefined, {
                      maximumFractionDigits: 4,
                    })}
                  </TableCell>
                  <TableCell className="text-right font-mono text-emerald-400">
                    {parseFloat(event.taoAmount).toLocaleString(undefined, {
                      maximumFractionDigits: 4,
                    })}
                  </TableCell>
                  <TableCell className="text-right font-mono text-zinc-400">
                    {parseFloat(event.conversionRate).toFixed(4)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-blue-400">
                    {event.taoPrice != null ? `$${event.taoPrice.toFixed(2)}` : "—"}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={getConversionStatus(event)} />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewAllocation(event.id)}
                      className="text-zinc-400 hover:text-zinc-200"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Allocation Dialog */}
      <Dialog open={showAllocationDialog} onOpenChange={setShowAllocationDialog}>
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">
              Allocation Details:{" "}
              {selectedConversion
                ? selectedConversion.id.length > 16
                  ? selectedConversion.id.slice(0, 12) + "..."
                  : selectedConversion.id
                : ""}
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              Pro-rata TAO allocation across all delegators for this conversion
              event
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">Total dTAO Sold</div>
                <div className="text-lg font-mono text-zinc-100">
                  {selectedConversion
                    ? parseFloat(selectedConversion.dtaoAmount).toLocaleString(
                        undefined,
                        { maximumFractionDigits: 4 }
                      )
                    : "—"}
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Total TAO Received
                </div>
                <div className="text-lg font-mono text-emerald-400">
                  {selectedConversion
                    ? parseFloat(selectedConversion.taoAmount).toLocaleString(
                        undefined,
                        { maximumFractionDigits: 4 }
                      )
                    : "—"}
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Allocations
                </div>
                <div className="text-lg font-mono text-zinc-100">
                  {conversionDetail
                    ? conversionDetail.allocations.length
                    : "—"}
                </div>
              </div>
            </div>

            {/* Allocation Table */}
            <div className="border border-zinc-800 rounded-lg overflow-hidden">
              {detailLoading ? (
                <div className="flex items-center justify-center py-12 text-zinc-400">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  Loading allocations...
                </div>
              ) : conversionDetail &&
                conversionDetail.allocations.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                      <TableHead className="text-zinc-400">Allocation ID</TableHead>
                      <TableHead className="text-zinc-400 text-right">
                        TAO Allocated
                      </TableHead>
                      <TableHead className="text-zinc-400">Method</TableHead>
                      <TableHead className="text-zinc-400">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {conversionDetail.allocations.map((alloc) => (
                      <TableRow
                        key={alloc.id}
                        className="border-zinc-800 hover:bg-zinc-800/50"
                      >
                        <TableCell className="font-mono text-xs text-zinc-300">
                          {alloc.id.slice(0, 8)}...
                        </TableCell>
                        <TableCell className="text-right font-mono text-emerald-400">
                          {parseFloat(alloc.taoAllocated).toLocaleString(
                            undefined,
                            { maximumFractionDigits: 4 }
                          )}
                        </TableCell>
                        <TableCell className="text-zinc-400 text-sm">
                          {alloc.allocationMethod || "—"}
                        </TableCell>
                        <TableCell>
                          <StatusBadge
                            status={
                              alloc.completenessFlag === "complete"
                                ? "complete"
                                : "partial"
                            }
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-zinc-500 text-sm">
                  No allocations yet for this conversion event.
                </div>
              )}
            </div>

            {/* Sum Check */}
            {conversionDetail && conversionDetail.allocations.length > 0 && (
              <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <Check className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 space-y-1 text-sm">
                    <div className="text-emerald-400 font-medium">
                      Sum Check
                    </div>
                    <div className="text-zinc-300 font-mono">
                      &Sigma; TAO Allocated ={" "}
                      {conversionDetail.allocations
                        .reduce(
                          (acc, a) => acc + parseFloat(a.taoAllocated),
                          0
                        )
                        .toLocaleString(undefined, {
                          maximumFractionDigits: 4,
                        })}{" "}
                      TAO
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
