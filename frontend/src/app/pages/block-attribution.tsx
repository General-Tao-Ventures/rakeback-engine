import { useState, useEffect, useCallback } from "react";
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
import { ExternalLink, RefreshCw, Loader2, Download, AlertTriangle } from "lucide-react";
import { useBlockchain } from "../../hooks/use-blockchain";
import { toast } from "sonner";
import { backendService, type Attribution, type IngestionResult } from "../../services/backend-service";

interface GroupedBlock {
  blockNumber: number;
  subnet: string;
  hotkey: string;
  totalDtao: string;
  delegatorCount: number;
  status: StatusType;
  timestamp: string;
}

function groupAttributionsByBlock(attributions: Attribution[]): GroupedBlock[] {
  const map = new Map<
    number,
    { hotkey: string; subnet: string; totalDtao: number; delegators: Set<string>; flags: Set<string> }
  >();

  for (const attr of attributions) {
    let entry = map.get(attr.blockNumber);
    if (!entry) {
      entry = { hotkey: attr.validatorHotkey, subnet: "", totalDtao: 0, delegators: new Set(), flags: new Set() };
      map.set(attr.blockNumber, entry);
    }
    entry.totalDtao += parseFloat(attr.attributedDtao);
    entry.delegators.add(attr.delegatorAddress);
    entry.flags.add(attr.completenessFlag);
    if (attr.subnetId != null) {
      entry.subnet = attr.subnetId === 0 ? "ROOT" : `SN${attr.subnetId}`;
    }
  }

  const blocks: GroupedBlock[] = [];
  for (const [blockNumber, entry] of map) {
    let status: StatusType = "complete";
    if (entry.flags.has("missing") || entry.flags.has("incomplete")) status = "missing";
    else if (entry.flags.has("partial")) status = "partial";

    blocks.push({
      blockNumber,
      subnet: entry.subnet || "—",
      hotkey: entry.hotkey.length > 14 ? entry.hotkey.slice(0, 14) + "..." : entry.hotkey,
      totalDtao: entry.totalDtao.toFixed(4),
      delegatorCount: entry.delegators.size,
      status,
      timestamp: "",
    });
  }

  blocks.sort((a, b) => b.blockNumber - a.blockNumber);
  return blocks;
}

// Persist list data + filters across list ↔ detail navigation so returning doesn't blank the list.
let listCache: {
  data: GroupedBlock[];
  blockRange: string;
  subnet: string;
  hotkey: string;
  customStartBlock: string;
  customEndBlock: string;
} | null = null;

export default function BlockAttribution() {
  const blockchain = useBlockchain();
  const [blockRange, setBlockRange] = useState(() => listCache?.blockRange ?? "latest-100");
  const [subnet, setSubnet] = useState(() => listCache?.subnet ?? "all");
  const [hotkey, setHotkey] = useState(() => listCache?.hotkey ?? "");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [customStartBlock, setCustomStartBlock] = useState(() => listCache?.customStartBlock ?? "");
  const [customEndBlock, setCustomEndBlock] = useState(() => listCache?.customEndBlock ?? "");
  const [isFetching, setIsFetching] = useState(false);

  const [data, setData] = useState<GroupedBlock[]>(() => listCache?.data ?? []);
  const [loading, setLoading] = useState(false);

  // Ingestion state
  const [ingestStartBlock, setIngestStartBlock] = useState("");
  const [ingestEndBlock, setIngestEndBlock] = useState("");
  const [ingestHotkey, setIngestHotkey] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestionResult | null>(null);
  const [ingestElapsed, setIngestElapsed] = useState(0);

  const currentBlock = blockchain.currentBlock || 4527342;
  const currentTime = new Date();
  const blockTime = 12;

  const blocksPerDay = Math.floor((24 * 60 * 60) / blockTime);
  const yesterdayStartBlock = currentBlock - blocksPerDay;
  const yesterdayEndBlock = currentBlock - 1;

  const todayStartTime = new Date(currentTime);
  todayStartTime.setHours(0, 0, 0, 0);
  const secondsSinceMidnight = Math.floor(
    (currentTime.getTime() - todayStartTime.getTime()) / 1000
  );
  const blocksSinceMidnight = Math.floor(secondsSinceMidnight / blockTime);
  const todayStartBlock = currentBlock - blocksSinceMidnight;

  const endOfDay = new Date(currentTime);
  endOfDay.setHours(23, 59, 59, 999);
  const secondsUntilMidnight = Math.floor(
    (endOfDay.getTime() - currentTime.getTime()) / 1000
  );
  const blocksUntilMidnight = Math.floor(secondsUntilMidnight / blockTime);
  const todayEndBlock = currentBlock + blocksUntilMidnight;

  const getBlockRangeForQuery = useCallback((): [number, number] => {
    if (blockRange === "custom") {
      const s = parseInt(customStartBlock) || currentBlock - 100;
      const e = parseInt(customEndBlock) || currentBlock;
      return [s, e];
    }
    const count = blockRange === "latest-1000" ? 1000 : blockRange === "latest-10000" ? 10000 : 100;
    return [currentBlock - count, currentBlock];
  }, [blockRange, customStartBlock, customEndBlock, currentBlock]);

  const fetchData = useCallback(
    async (opts?: { showFeedback?: boolean }) => {
      setLoading(true);
      try {
        const [start, end] = getBlockRangeForQuery();
        const subnetId = subnet === "all" ? undefined : subnet === "root" ? 0 : parseInt(subnet.replace("sn", ""));
        const attrs = await backendService.getAttributions(start, end, {
          validator_hotkey: hotkey || undefined,
          subnet_id: subnetId,
        });
        const grouped = groupAttributionsByBlock(attrs);
        setData(grouped);
        listCache = {
          data: grouped,
          blockRange,
          subnet,
          hotkey,
          customStartBlock,
          customEndBlock,
        };
        if (opts?.showFeedback && grouped.length === 0) {
          toast.info("No attributions found for this range. Ingest block data first.");
        }
      } catch (err) {
        console.error("Failed to fetch attributions:", err);
        setData([]);
        toast.error("Failed to fetch attributions. Is the backend running on port 8000?");
      } finally {
        setLoading(false);
      }
    },
    [getBlockRangeForQuery, subnet, hotkey, blockRange, customStartBlock, customEndBlock]
  );

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleFetchCurrentBlock = async () => {
    setIsFetching(true);
    try {
      if (blockchain.status !== "connected") {
        await blockchain.connect();
      }
      const block = await blockchain.getCurrentBlock();
      toast.success(`Fetched current block: ${block.toLocaleString()}`);
    } catch (error) {
      toast.error("Failed to fetch current block. Check API Settings.");
      console.error(error);
    } finally {
      setIsFetching(false);
    }
  };

  const handleIngest = async () => {
    const start = parseInt(ingestStartBlock);
    const end = parseInt(ingestEndBlock);
    const hk = ingestHotkey.trim();

    if (!start || !end || !hk) {
      toast.error("Please fill in start block, end block, and validator hotkey.");
      return;
    }
    if (end < start) {
      toast.error("End block must be >= start block.");
      return;
    }
    if (end - start > 500) {
      toast.error("Maximum 500 blocks per ingestion. Use a smaller range.");
      return;
    }

    setIngesting(true);
    setIngestResult(null);
    setIngestElapsed(0);
    const startTime = Date.now();
    const timer = setInterval(() => setIngestElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000);

    try {
      const result = await backendService.triggerIngestion(start, end, hk);
      setIngestResult(result);
      if (result.attributionsCreated > 0) {
        toast.success(`Ingested ${result.attributionsCreated} attributions across ${result.blocksCreated} blocks.`);
        // Auto-refresh table with the ingested range
        setBlockRange("custom");
        setCustomStartBlock(String(start));
        setCustomEndBlock(String(end));
        setHotkey(hk);
        // Trigger a re-fetch after short delay so state updates propagate
        setTimeout(() => fetchData(), 500);
      } else if (result.errors.length > 0) {
        toast.error(`Ingestion completed with errors. ${result.errors.length} error(s).`);
      } else {
        toast.warning("Ingestion completed but no attributions were created. The validator may not have delegations in this block range.");
      }
    } catch (err) {
      console.error("Ingestion failed:", err);
      toast.error("Ingestion request failed. Check that the backend is running.");
    } finally {
      clearInterval(timer);
      setIngesting(false);
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

          <div className="flex justify-end pt-2">
            <Button
              onClick={() => fetchData({ showFeedback: true })}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Search
            </Button>
          </div>

          {/* Custom Range Inputs */}
          {blockRange === "custom" && (
            <div className="pt-4 border-t border-zinc-800">
              <div className="grid grid-cols-2 gap-6">
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

      {/* Ingest Blocks Panel */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
        <div className="flex items-start gap-3 mb-4">
          <Download className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-zinc-50">Ingest Block Data</h3>
            <p className="text-sm text-zinc-400 mt-0.5">
              Fetch on-chain snapshots, yields, and compute attributions for a block range.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="space-y-2">
            <Label htmlFor="ingest-start" className="text-zinc-300 text-sm">
              Start Block
            </Label>
            <Input
              id="ingest-start"
              type="number"
              placeholder="e.g., 7574300"
              value={ingestStartBlock}
              onChange={(e) => setIngestStartBlock(e.target.value)}
              disabled={ingesting}
              className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono placeholder:text-zinc-500"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ingest-end" className="text-zinc-300 text-sm">
              End Block
            </Label>
            <Input
              id="ingest-end"
              type="number"
              placeholder="e.g., 7574305"
              value={ingestEndBlock}
              onChange={(e) => setIngestEndBlock(e.target.value)}
              disabled={ingesting}
              className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono placeholder:text-zinc-500"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label htmlFor="ingest-hotkey" className="text-zinc-300 text-sm">
              Validator Hotkey
            </Label>
            <Input
              id="ingest-hotkey"
              placeholder="e.g., 5Gq2gs4ft..."
              value={ingestHotkey}
              onChange={(e) => setIngestHotkey(e.target.value)}
              disabled={ingesting}
              className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono placeholder:text-zinc-500"
            />
          </div>
        </div>

        {/* Warning note */}
        <div className="flex items-start gap-2 mb-4 p-3 bg-amber-950/20 border border-amber-900/40 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-amber-300/80 leading-relaxed">
            <span className="font-medium text-amber-300">Heads up:</span> Each block
            requires multiple RPC calls to the archive node. Expect{" "}
            <span className="font-mono">~5-30s per block</span> depending on network
            latency and how many subnets the validator is active on. Start with a small
            range (5-10 blocks) to test, then scale up. Max 500 blocks per request.
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Button
            onClick={handleIngest}
            disabled={ingesting || !ingestStartBlock || !ingestEndBlock || !ingestHotkey.trim()}
            className="bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50"
          >
            {ingesting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Ingesting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Ingest Blocks
              </>
            )}
          </Button>

          {/* Live elapsed timer while ingesting */}
          {ingesting && (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <div className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
              <span>
                Processing {parseInt(ingestEndBlock) - parseInt(ingestStartBlock) + 1} blocks...{" "}
                <span className="font-mono text-zinc-300">{ingestElapsed}s</span> elapsed
              </span>
            </div>
          )}

          {/* Result summary after completion */}
          {!ingesting && ingestResult && (
            <div className="flex items-center gap-3 text-sm">
              {ingestResult.attributionsCreated > 0 ? (
                <span className="text-emerald-400">
                  {ingestResult.attributionsCreated} attributions created across{" "}
                  {ingestResult.blocksCreated} blocks
                </span>
              ) : (
                <span className="text-amber-400">
                  No attributions created
                  {ingestResult.errors.length > 0
                    ? ` (${ingestResult.errors.length} errors)`
                    : ""}
                </span>
              )}
              {ingestResult.blocksSkipped > 0 && (
                <span className="text-zinc-500">
                  ({ingestResult.blocksSkipped} skipped — already ingested)
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error details expandable */}
        {!ingesting && ingestResult && ingestResult.errors.length > 0 && (
          <details className="mt-3">
            <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400">
              Show {ingestResult.errors.length} error(s)
            </summary>
            <div className="mt-2 max-h-32 overflow-y-auto rounded bg-zinc-950 border border-zinc-800 p-2">
              {ingestResult.errors.map((err, i) => (
                <div key={i} className="text-xs text-red-400/80 font-mono truncate">
                  {err}
                </div>
              ))}
            </div>
          </details>
        )}
      </div>

      {/* Table */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        {loading && data.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-zinc-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Loading attributions...
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-16 text-zinc-500">
            <p className="text-lg mb-1">No attributions found</p>
            <p className="text-sm">
              Ingest block data first using the API, then attributions will appear here.
            </p>
          </div>
        ) : (
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
              {data.map((row) => (
                <TableRow
                  key={row.blockNumber}
                  className="border-zinc-800 hover:bg-zinc-800/50 transition-colors cursor-pointer"
                >
                  <TableCell className="font-mono text-zinc-100">
                    {row.blockNumber.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-zinc-400 text-sm">
                    {row.timestamp || "—"}
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
        )}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Blocks</div>
          <div className="text-2xl font-mono text-zinc-100">
            {data.length.toLocaleString()}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total dTAO</div>
          <div className="text-2xl font-mono text-zinc-100">
            {data
              .reduce((acc, row) => acc + parseFloat(row.totalDtao), 0)
              .toFixed(4)}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Complete</div>
          <div className="text-2xl font-mono text-emerald-400">
            {data.filter((r) => r.status === "complete").length}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Requires Review</div>
          <div className="text-2xl font-mono text-amber-400">
            {
              data.filter(
                (r) => r.status === "partial" || r.status === "missing"
              ).length
            }
          </div>
        </div>
      </div>
    </div>
  );
}
