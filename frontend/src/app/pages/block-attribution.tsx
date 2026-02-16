import { useState } from "react";
import { Link } from "react-router";
import { StatusBadge, StatusType } from "../components/status-badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Button } from "../components/ui/button";
import { ExternalLink, RefreshCw } from "lucide-react";
import { useBlockchain } from "../../hooks/use-blockchain";
import { toast } from "sonner";

interface BlockAttribution {
  blockNumber: number;
  subnet: string;
  hotkey: string;
  totalDtao: string;
  delegatorCount: number;
  status: StatusType;
  timestamp: string;
}

const mockData: BlockAttribution[] = [
  {
    blockNumber: 4521893,
    subnet: "SN1",
    hotkey: "5G9RtsTbiYJ...",
    totalDtao: "142.5847",
    delegatorCount: 47,
    status: "complete",
    timestamp: "2026-02-14 08:23:41",
  },
  {
    blockNumber: 4521892,
    subnet: "SN21",
    hotkey: "5HK8d9Zy2aB...",
    totalDtao: "89.2103",
    delegatorCount: 32,
    status: "complete",
    timestamp: "2026-02-14 08:23:29",
  },
  {
    blockNumber: 4521891,
    subnet: "SN1",
    hotkey: "5G9RtsTbiYJ...",
    totalDtao: "156.8921",
    delegatorCount: 47,
    status: "complete",
    timestamp: "2026-02-14 08:23:17",
  },
  {
    blockNumber: 4521890,
    subnet: "SN8",
    hotkey: "5FnL7qR3mV9...",
    totalDtao: "0.0000",
    delegatorCount: 0,
    status: "partial",
    timestamp: "2026-02-14 08:23:05",
  },
  {
    blockNumber: 4521889,
    subnet: "SN21",
    hotkey: "5HK8d9Zy2aB...",
    totalDtao: "94.7652",
    delegatorCount: 32,
    status: "complete",
    timestamp: "2026-02-14 08:22:53",
  },
  {
    blockNumber: 4521888,
    subnet: "SN1",
    hotkey: "5G9RtsTbiYJ...",
    totalDtao: "148.3394",
    delegatorCount: 47,
    status: "complete",
    timestamp: "2026-02-14 08:22:41",
  },
  {
    blockNumber: 4521887,
    subnet: "ROOT",
    hotkey: "5D5PhZQNJc7...",
    totalDtao: "23.4102",
    delegatorCount: 12,
    status: "missing",
    timestamp: "2026-02-14 08:22:29",
  },
  {
    blockNumber: 4521886,
    subnet: "SN21",
    hotkey: "5HK8d9Zy2aB...",
    totalDtao: "91.5473",
    delegatorCount: 32,
    status: "complete",
    timestamp: "2026-02-14 08:22:17",
  },
];

export default function BlockAttribution() {
  const blockchain = useBlockchain();
  const [blockRange, setBlockRange] = useState("latest-100");
  const [subnet, setSubnet] = useState("all");
  const [hotkey, setHotkey] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [customStartBlock, setCustomStartBlock] = useState("");
  const [customEndBlock, setCustomEndBlock] = useState("");
  const [isFetching, setIsFetching] = useState(false);

  // Use blockchain current block if available, otherwise use mock
  const currentBlock = blockchain.currentBlock || 4527342;
  const currentTime = new Date();
  const blockTime = 12; // seconds per block

  // Calculate yesterday's range (24 hours ago)
  const blocksPerDay = Math.floor((24 * 60 * 60) / blockTime); // 7,200 blocks
  const yesterdayStartBlock = currentBlock - blocksPerDay;
  const yesterdayEndBlock = currentBlock - 1;

  // Calculate today's predicted range
  const todayStartTime = new Date(currentTime);
  todayStartTime.setHours(0, 0, 0, 0);
  const secondsSinceMidnight = Math.floor(
    (currentTime.getTime() - todayStartTime.getTime()) / 1000
  );
  const blocksSinceMidnight = Math.floor(secondsSinceMidnight / blockTime);
  const todayStartBlock = currentBlock - blocksSinceMidnight;

  // Predict end of day
  const endOfDay = new Date(currentTime);
  endOfDay.setHours(23, 59, 59, 999);
  const secondsUntilMidnight = Math.floor(
    (endOfDay.getTime() - currentTime.getTime()) / 1000
  );
  const blocksUntilMidnight = Math.floor(secondsUntilMidnight / blockTime);
  const todayEndBlock = currentBlock + blocksUntilMidnight;

  const handleFetchCurrentBlock = async () => {
    setIsFetching(true);
    try {
      // Connect if not already connected
      if (blockchain.status !== "connected") {
        await blockchain.connect();
      }

      // Fetch current block
      const block = await blockchain.getCurrentBlock();
      
      toast.success(`Fetched current block: ${block.toLocaleString()}`);
    } catch (error) {
      toast.error("Failed to fetch current block. Check API Settings.");
      console.error(error);
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Block Attribution Dashboard
        </h2>
        <p className="text-sm text-zinc-400">
          Deterministic and auditable yield attribution per block. Click any
          row for full delegator breakdown.
        </p>
      </div>

      {/* Block Range Status Cards */}
      <div className="grid grid-cols-3 gap-4">
        {/* Current Block */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1.5">
            Current Block
          </div>
          <div className="text-2xl font-semibold text-emerald-400 font-mono">
            {currentBlock.toLocaleString()}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {currentTime.toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </div>
          <Button
            className="mt-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100"
            onClick={handleFetchCurrentBlock}
            disabled={isFetching}
          >
            {isFetching ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Refresh
          </Button>
        </div>

        {/* Today's Predicted Range */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1.5">
            Today's Block Range (Predicted)
          </div>
          <div className="text-lg font-semibold text-blue-400 font-mono">
            {todayStartBlock.toLocaleString()} - {todayEndBlock.toLocaleString()}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {blocksSinceMidnight.toLocaleString()} blocks processed •{" "}
            {blocksUntilMidnight.toLocaleString()} remaining
          </div>
        </div>

        {/* Yesterday's Range */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1.5">
            Yesterday's Block Range (24h)
          </div>
          <div className="text-lg font-semibold text-zinc-400 font-mono">
            {yesterdayStartBlock.toLocaleString()} - {yesterdayEndBlock.toLocaleString()}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {blocksPerDay.toLocaleString()} blocks total
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="block-range" className="text-zinc-300">
                Block Range
              </Label>
              <Select value={blockRange} onValueChange={setBlockRange}>
                <SelectTrigger
                  id="block-range"
                  className="bg-zinc-900 border-zinc-700 text-zinc-100"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-700">
                  <SelectItem value="latest-100">Latest 100 blocks</SelectItem>
                  <SelectItem value="latest-1000">Latest 1,000 blocks</SelectItem>
                  <SelectItem value="latest-10000">
                    Latest 10,000 blocks
                  </SelectItem>
                  <SelectItem value="custom">Custom range</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subnet" className="text-zinc-300">
                Subnet
              </Label>
              <Select value={subnet} onValueChange={setSubnet}>
                <SelectTrigger
                  id="subnet"
                  className="bg-zinc-900 border-zinc-700 text-zinc-100"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-700">
                  <SelectItem value="all">All Subnets</SelectItem>
                  <SelectItem value="root">ROOT</SelectItem>
                  <SelectItem value="sn1">SN1</SelectItem>
                  <SelectItem value="sn8">SN8</SelectItem>
                  <SelectItem value="sn21">SN21</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2 col-span-2">
              <Label htmlFor="hotkey" className="text-zinc-300">
                Hotkey Filter
              </Label>
              <Input
                id="hotkey"
                placeholder="Enter hotkey address (e.g., 5G9Rts...)"
                value={hotkey}
                onChange={(e) => setHotkey(e.target.value)}
                className="bg-zinc-900 border-zinc-700 text-zinc-100 placeholder:text-zinc-500"
              />
            </div>
          </div>

          {/* Custom Range Inputs - Show when custom is selected */}
          {blockRange === "custom" && (
            <div className="pt-4 border-t border-zinc-800">
              <div className="grid grid-cols-2 gap-6">
                {/* Date Range Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-px flex-1 bg-zinc-800"></div>
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                      Date Range
                    </span>
                    <div className="h-px flex-1 bg-zinc-800"></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="start-date" className="text-zinc-300 text-sm">
                        Start Date
                      </Label>
                      <Input
                        id="start-date"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="bg-zinc-900 border-zinc-700 text-zinc-100 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:opacity-50"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="end-date" className="text-zinc-300 text-sm">
                        End Date
                      </Label>
                      <Input
                        id="end-date"
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="bg-zinc-900 border-zinc-700 text-zinc-100 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:opacity-50"
                      />
                    </div>
                  </div>
                  {startDate && endDate && (
                    <div className="text-xs text-zinc-500 font-mono">
                      Estimated range: ~{Math.floor(
                        (new Date(endDate).getTime() - new Date(startDate).getTime()) / 1000 / 12
                      ).toLocaleString()} blocks
                    </div>
                  )}
                </div>

                {/* Block Range Section */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-px flex-1 bg-zinc-800"></div>
                    <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                      Block Range
                    </span>
                    <div className="h-px flex-1 bg-zinc-800"></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="start-block" className="text-zinc-300 text-sm">
                        Start Block
                      </Label>
                      <Input
                        id="start-block"
                        type="number"
                        placeholder="e.g., 4521800"
                        value={customStartBlock}
                        onChange={(e) => setCustomStartBlock(e.target.value)}
                        className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono placeholder:text-zinc-500"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="end-block" className="text-zinc-300 text-sm">
                        End Block
                      </Label>
                      <Input
                        id="end-block"
                        type="number"
                        placeholder="e.g., 4521900"
                        value={customEndBlock}
                        onChange={(e) => setCustomEndBlock(e.target.value)}
                        className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono placeholder:text-zinc-500"
                      />
                    </div>
                  </div>
                  {customStartBlock && customEndBlock && (
                    <div className="text-xs text-zinc-500 font-mono">
                      Range: {(parseInt(customEndBlock) - parseInt(customStartBlock)).toLocaleString()} blocks
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Block Number</TableHead>
              <TableHead className="text-zinc-400">Timestamp</TableHead>
              <TableHead className="text-zinc-400">Subnet</TableHead>
              <TableHead className="text-zinc-400">Hotkey</TableHead>
              <TableHead className="text-zinc-400 text-right">
                Total dTAO
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Delegators
              </TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
              <TableHead className="text-zinc-400"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockData.map((row) => (
              <TableRow
                key={row.blockNumber}
                className="border-zinc-800 hover:bg-zinc-800/50 transition-colors cursor-pointer"
              >
                <TableCell className="font-mono text-zinc-100">
                  {row.blockNumber.toLocaleString()}
                </TableCell>
                <TableCell className="text-zinc-400 text-sm">
                  {row.timestamp}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                    {row.subnet}
                  </span>
                </TableCell>
                <TableCell className="font-mono text-sm text-zinc-400">
                  {row.hotkey}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {row.totalDtao}
                </TableCell>
                <TableCell className="text-right text-zinc-400">
                  {row.delegatorCount}
                </TableCell>
                <TableCell>
                  <StatusBadge status={row.status} />
                </TableCell>
                <TableCell>
                  <Link
                    to={`/block-detail/${row.blockNumber}`}
                    className="text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Blocks</div>
          <div className="text-2xl font-mono text-zinc-100">
            {mockData.length.toLocaleString()}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total dTAO</div>
          <div className="text-2xl font-mono text-zinc-100">
            {mockData
              .reduce((acc, row) => acc + parseFloat(row.totalDtao), 0)
              .toFixed(4)}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Complete</div>
          <div className="text-2xl font-mono text-emerald-400">
            {mockData.filter((r) => r.status === "complete").length}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Requires Review</div>
          <div className="text-2xl font-mono text-amber-400">
            {
              mockData.filter(
                (r) => r.status === "partial" || r.status === "missing"
              ).length
            }
          </div>
        </div>
      </div>
    </div>
  );
}