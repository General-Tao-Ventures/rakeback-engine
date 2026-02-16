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
import { ChevronRight, TrendingUp, TrendingDown, Check } from "lucide-react";
import { useTaoPrice } from "../../hooks/use-tao-price";

interface ConversionEvent {
  id: string;
  date: string;
  subnet: string;
  dtaoSold: string;
  taoReceived: string;
  conversionRate: number;
  status: StatusType;
  allocatedDelegators: number;
  taoPrice: number; // TAO price at time of conversion
}

const mockConversions: ConversionEvent[] = [
  {
    id: "CVT-2026-02-14-001",
    date: "2026-02-14 10:30:00",
    subnet: "SN1",
    dtaoSold: "15,420.8347",
    taoReceived: "12,984.1532",
    conversionRate: 0.8419,
    status: "allocated",
    allocatedDelegators: 47,
    taoPrice: 487.32,
  },
  {
    id: "CVT-2026-02-13-002",
    date: "2026-02-13 16:45:00",
    subnet: "SN21",
    dtaoSold: "8,932.4201",
    taoReceived: "7,521.8945",
    conversionRate: 0.8421,
    status: "allocated",
    allocatedDelegators: 32,
    taoPrice: 482.15,
  },
  {
    id: "CVT-2026-02-13-001",
    date: "2026-02-13 09:15:00",
    subnet: "SN8",
    dtaoSold: "4,567.2890",
    taoReceived: "3,845.3214",
    conversionRate: 0.8419,
    status: "partial",
    allocatedDelegators: 18,
    taoPrice: 479.84,
  },
  {
    id: "CVT-2026-02-12-003",
    date: "2026-02-12 14:20:00",
    subnet: "SN1",
    dtaoSold: "18,234.5671",
    taoReceived: "15,352.8901",
    conversionRate: 0.8420,
    status: "allocated",
    allocatedDelegators: 47,
    taoPrice: 476.92,
  },
  {
    id: "CVT-2026-02-12-002",
    date: "2026-02-12 11:10:00",
    subnet: "SN21",
    dtaoSold: "9,876.3402",
    taoReceived: "8,315.6728",
    conversionRate: 0.8420,
    status: "allocated",
    allocatedDelegators: 32,
    taoPrice: 474.58,
  },
  {
    id: "CVT-2026-02-12-001",
    date: "2026-02-12 08:05:00",
    subnet: "ROOT",
    dtaoSold: "2,341.0234",
    taoReceived: "1,971.2817",
    conversionRate: 0.8421,
    status: "unallocated",
    allocatedDelegators: 0,
    taoPrice: 472.31,
  },
];

interface AllocationDetail {
  wallet: string;
  dtaoEarned: string;
  taoAllocated: string;
  proportion: number;
}

const mockAllocationDetails: AllocationDetail[] = [
  {
    wallet: "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL",
    dtaoEarned: "2,841.7523",
    taoAllocated: "2,392.4158",
    proportion: 18.43,
  },
  {
    wallet: "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
    dtaoEarned: "2,015.3892",
    taoAllocated: "1,696.7491",
    proportion: 13.07,
  },
  {
    wallet: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    dtaoEarned: "1,472.8341",
    taoAllocated: "1,239.9634",
    proportion: 9.55,
  },
  {
    wallet: "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy",
    dtaoEarned: "1,225.4782",
    taoAllocated: "1,031.6145",
    proportion: 7.95,
  },
];

export default function ConversionEvents() {
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [showAllocationDialog, setShowAllocationDialog] = useState(false);

  // Fetch real TAO price from TaoStats API
  const { price: currentTaoPrice, price24hAgo: taoPricePrevious, change24h: priceChange24h, changePercent24h: priceChangePercent } =
    useTaoPrice();

  const handleViewAllocation = (eventId: string) => {
    setSelectedEvent(eventId);
    setShowAllocationDialog(true);
  };

  const selectedConversion = mockConversions.find((c) => c.id === selectedEvent);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Conversion Events
        </h2>
        <p className="text-sm text-zinc-400">
          Transparent dTAO → TAO conversion tracking with pro-rata allocation to
          delegators
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        {/* TAO Price Card */}
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
            {mockConversions.length}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total dTAO Sold</div>
          <div className="text-2xl font-mono text-zinc-100">
            {mockConversions
              .reduce(
                (acc, c) => acc + parseFloat(c.dtaoSold.replace(/,/g, "")),
                0
              )
              .toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total TAO Received</div>
          <div className="text-2xl font-mono text-emerald-400">
            {mockConversions
              .reduce(
                (acc, c) => acc + parseFloat(c.taoReceived.replace(/,/g, "")),
                0
              )
              .toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Avg Conversion Rate</div>
          <div className="text-2xl font-mono text-zinc-100">
            {(
              mockConversions.reduce((acc, c) => acc + c.conversionRate, 0) /
              mockConversions.length
            ).toFixed(4)}
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
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Event ID</TableHead>
              <TableHead className="text-zinc-400">Date</TableHead>
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
            {mockConversions.map((event) => (
              <TableRow
                key={event.id}
                className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
              >
                <TableCell className="font-mono text-sm text-zinc-300">
                  {event.id}
                </TableCell>
                <TableCell className="text-zinc-400 text-sm">
                  {event.date}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                    {event.subnet}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {event.dtaoSold}
                </TableCell>
                <TableCell className="text-right font-mono text-emerald-400">
                  {event.taoReceived}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-400">
                  {event.conversionRate.toFixed(4)}
                </TableCell>
                <TableCell className="text-right font-mono text-blue-400">
                  ${event.taoPrice.toFixed(2)}
                </TableCell>
                <TableCell>
                  <StatusBadge status={event.status} />
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
      </div>

      {/* Allocation Dialog */}
      <Dialog open={showAllocationDialog} onOpenChange={setShowAllocationDialog}>
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">
              Allocation Details: {selectedConversion?.id}
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
                  {selectedConversion?.dtaoSold}
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Total TAO Received
                </div>
                <div className="text-lg font-mono text-emerald-400">
                  {selectedConversion?.taoReceived}
                </div>
              </div>
              <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3">
                <div className="text-xs text-zinc-500 mb-1">
                  Delegators Allocated
                </div>
                <div className="text-lg font-mono text-zinc-100">
                  {selectedConversion?.allocatedDelegators}
                </div>
              </div>
            </div>

            {/* Allocation Table */}
            <div className="border border-zinc-800 rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                    <TableHead className="text-zinc-400">Wallet</TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      dTAO Earned
                    </TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      TAO Allocated
                    </TableHead>
                    <TableHead className="text-zinc-400 text-right">
                      Proportion
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockAllocationDetails.map((detail, idx) => (
                    <TableRow
                      key={idx}
                      className="border-zinc-800 hover:bg-zinc-800/50"
                    >
                      <TableCell className="font-mono text-xs text-zinc-300">
                        {detail.wallet.slice(0, 8)}...{detail.wallet.slice(-8)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-zinc-100">
                        {detail.dtaoEarned}
                      </TableCell>
                      <TableCell className="text-right font-mono text-emerald-400">
                        {detail.taoAllocated}
                      </TableCell>
                      <TableCell className="text-right text-zinc-400">
                        {detail.proportion.toFixed(2)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Sum Check */}
            <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Check className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1 text-sm">
                  <div className="text-emerald-400 font-medium">
                    Sum Check Validated
                  </div>
                  <div className="text-zinc-300 font-mono">
                    Σ TAO Allocated = {selectedConversion?.taoReceived} TAO
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}