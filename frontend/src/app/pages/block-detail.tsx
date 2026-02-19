import { useState, useEffect } from "react";
import { useParams, Link } from "react-router";
import { StatusBadge, StatusType } from "../components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { ArrowLeft, Check, Loader2, AlertTriangle } from "lucide-react";
import {
  backendService,
  type BlockDetail as BlockDetailData,
} from "../../services/backend-service";

export default function BlockDetail() {
  const { blockNumber } = useParams();
  const [detail, setDetail] = useState<BlockDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!blockNumber) return;
    const blockNum = parseInt(blockNumber);
    if (isNaN(blockNum)) return;

    setLoading(true);
    setError(null);
    backendService
      .getBlockDetail(blockNum)
      .then(setDetail)
      .catch((err) => {
        console.error("Failed to fetch block detail:", err);
        setError("No attribution data found for this block.");
      })
      .finally(() => setLoading(false));
  }, [blockNumber]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto flex items-center justify-center py-24 text-zinc-400">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Loading block detail...
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <Link
          to="/block-attribution"
          className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Block Attribution
        </Link>
        <div className="text-center py-16 text-zinc-500">
          <AlertTriangle className="h-8 w-8 mx-auto mb-3 text-amber-400" />
          <p className="text-lg mb-1">Block {blockNumber}</p>
          <p className="text-sm">{error || "No data available for this block."}</p>
        </div>
      </div>
    );
  }

  const attributions = detail.attributions;
  const totalDtao = attributions.reduce(
    (acc, a) => acc + parseFloat(a.attributedDtao),
    0
  );
  const totalTaoAllocated = attributions.reduce(
    (acc, a) => acc + parseFloat(a.taoAllocated),
    0
  );

  const completenessStatus: StatusType =
    detail.completenessFlag === "complete"
      ? "complete"
      : detail.completenessFlag === "partial"
        ? "partial"
        : "missing";

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Back Button */}
      <Link
        to="/block-attribution"
        className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Block Attribution
      </Link>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-semibold text-zinc-50">
            Block {detail.blockNumber.toLocaleString()}
          </h2>
          <StatusBadge status={completenessStatus} />
        </div>
        <p className="text-sm text-zinc-400">
          Forensic view of all delegator attributions for this block
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Block Number</div>
          <div className="text-xl font-mono text-zinc-100">
            {detail.blockNumber.toLocaleString()}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Timestamp</div>
          <div className="text-sm text-zinc-100">
            {detail.timestamp
              ? new Date(detail.timestamp).toLocaleString()
              : "—"}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Attributed dTAO</div>
          <div className="text-xl font-mono text-zinc-100">
            {totalDtao.toFixed(4)}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">TAO Allocated</div>
          <div className="text-xl font-mono text-emerald-400">
            {totalTaoAllocated.toFixed(4)}
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
        <h3 className="font-medium text-zinc-50 mb-4">Block Metadata</h3>
        <div className="grid grid-cols-3 gap-6 text-sm">
          <div>
            <div className="text-zinc-500 mb-1">Validator Hotkey</div>
            <div className="text-zinc-100 font-mono text-xs break-all">
              {detail.validatorHotkey}
            </div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Total Delegators</div>
            <div className="text-zinc-100">{detail.delegatorCount}</div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Attribution Status</div>
            <div className="flex items-center gap-2">
              <StatusBadge status={completenessStatus} />
            </div>
          </div>
        </div>
      </div>

      {/* Delegator Table */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h3 className="font-medium text-zinc-50">
            Delegator Attribution Breakdown
          </h3>
          <p className="text-sm text-zinc-400 mt-1">
            Pro-rata distribution based on stake at block height
          </p>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Delegator Wallet</TableHead>
              <TableHead className="text-zinc-400">Delegation Type</TableHead>
              <TableHead className="text-zinc-400">Subnet</TableHead>
              <TableHead className="text-zinc-400 text-right">
                Proportion
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Attributed dTAO
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                TAO Allocated
              </TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {attributions.map((attr) => (
              <TableRow
                key={attr.id}
                className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
              >
                <TableCell className="font-mono text-xs text-zinc-300">
                  {attr.delegatorAddress.slice(0, 8)}...
                  {attr.delegatorAddress.slice(-8)}
                </TableCell>
                <TableCell>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      attr.delegationType === "root_tao"
                        ? "bg-blue-950/50 text-blue-400 border border-blue-900/50"
                        : "bg-purple-950/50 text-purple-400 border border-purple-900/50"
                    }`}
                  >
                    {attr.delegationType === "root_tao" ? "TAO" : "dTAO"}
                  </span>
                </TableCell>
                <TableCell className="text-zinc-400 text-sm">
                  {attr.subnetId != null
                    ? attr.subnetId === 0
                      ? "ROOT"
                      : `SN${attr.subnetId}`
                    : "—"}
                </TableCell>
                <TableCell className="text-right text-zinc-400">
                  {(parseFloat(attr.delegationProportion) * 100).toFixed(2)}%
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {parseFloat(attr.attributedDtao).toFixed(4)}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-400">
                  {parseFloat(attr.taoAllocated).toFixed(4)}
                </TableCell>
                <TableCell>
                  {attr.fullyAllocated ? (
                    <StatusBadge status="allocated" />
                  ) : (
                    <StatusBadge status="unallocated" />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Sum Check */}
      <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-10 h-10 bg-emerald-950/50 border border-emerald-900/50 rounded-lg flex items-center justify-center">
            <Check className="h-5 w-5 text-emerald-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-emerald-400 mb-2">
              Sum Check
            </h3>
            <div className="space-y-1 text-sm text-zinc-300">
              <div className="flex justify-between font-mono">
                <span>Sum of delegator attributions:</span>
                <span>{totalDtao.toFixed(4)} dTAO</span>
              </div>
              <div className="flex justify-between font-mono">
                <span>Block total dTAO (from API):</span>
                <span>{parseFloat(detail.totalDtao).toFixed(4)} dTAO</span>
              </div>
              <div className="flex justify-between font-mono border-t border-emerald-900/30 pt-1 mt-1">
                <span className="text-emerald-400">Match:</span>
                <span className="text-emerald-400">
                  {Math.abs(totalDtao - parseFloat(detail.totalDtao)) < 0.0001
                    ? "Validated"
                    : "Mismatch"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
