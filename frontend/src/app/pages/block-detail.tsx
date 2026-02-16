import { useParams, Link } from "react-router";
import { StatusBadge } from "../components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { ArrowLeft, Check } from "lucide-react";

interface DelegatorAttribution {
  wallet: string;
  stakeAmount: string;
  stakeType: "TAO" | "dTAO";
  proportion: number;
  grossDtao: string;
  validatorRetained: string;
  partnerAttribution: string | null;
}

const mockDelegators: DelegatorAttribution[] = [
  {
    wallet: "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL",
    stakeAmount: "1,247.5820",
    stakeType: "TAO",
    proportion: 18.24,
    grossDtao: "26.0147",
    validatorRetained: "4.6826",
    partnerAttribution: "Creative Builds",
  },
  {
    wallet: "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
    stakeAmount: "892.3401",
    stakeType: "TAO",
    proportion: 13.04,
    grossDtao: "18.5974",
    validatorRetained: "3.3475",
    partnerAttribution: null,
  },
  {
    wallet: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    stakeAmount: "654.2890",
    stakeType: "dTAO",
    proportion: 9.56,
    grossDtao: "13.6326",
    validatorRetained: "2.4539",
    partnerAttribution: "Talisman",
  },
  {
    wallet: "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy",
    stakeAmount: "543.8920",
    stakeType: "TAO",
    proportion: 7.95,
    grossDtao: "11.3354",
    validatorRetained: "2.0404",
    partnerAttribution: null,
  },
  {
    wallet: "5HpG9w8EBLe5XCrbczpwq5TSXvedjrBGCwqxK1iQ7qUsSWFc",
    stakeAmount: "489.1120",
    stakeType: "TAO",
    proportion: 7.15,
    grossDtao: "10.1921",
    validatorRetained: "1.8346",
    partnerAttribution: "Creative Builds",
  },
  {
    wallet: "5EYCAe5ijiYfyeZ2JJCGq56LmPyNRAKzpG4QkoQkkQNB5e6Z",
    stakeAmount: "423.5670",
    stakeType: "dTAO",
    proportion: 6.19,
    grossDtao: "8.8261",
    validatorRetained: "1.5887",
    partnerAttribution: null,
  },
  {
    wallet: "5DfhGyQdFobKM8NsWvEeAKk5EQQgYe9AydgJ7rMB6E1EqRzV",
    stakeAmount: "387.9240",
    stakeType: "TAO",
    proportion: 5.67,
    grossDtao: "8.0826",
    validatorRetained: "1.4549",
    partnerAttribution: "Talisman",
  },
  {
    wallet: "5G1ojzh47Yt8KoYhuAjXpHcazvsoCXe3G8LZchKDvumozJJJ",
    stakeAmount: "312.4450",
    stakeType: "TAO",
    proportion: 4.57,
    grossDtao: "6.5131",
    validatorRetained: "1.1724",
    partnerAttribution: null,
  },
];

export default function BlockDetail() {
  const { blockNumber } = useParams();

  const totalStake = mockDelegators.reduce(
    (acc, d) => acc + parseFloat(d.stakeAmount.replace(/,/g, "")),
    0
  );
  const totalGrossDtao = mockDelegators.reduce(
    (acc, d) => acc + parseFloat(d.grossDtao),
    0
  );
  const totalRetained = mockDelegators.reduce(
    (acc, d) => acc + parseFloat(d.validatorRetained),
    0
  );

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
            Block {blockNumber?.toLocaleString()}
          </h2>
          <StatusBadge status="complete" />
        </div>
        <p className="text-sm text-zinc-400">
          Forensic view of all delegator attributions for this block
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Block Number</div>
          <div className="text-xl font-mono text-zinc-100">{blockNumber}</div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Timestamp</div>
          <div className="text-sm text-zinc-100">2026-02-14 08:23:41 UTC</div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">Total Gross dTAO</div>
          <div className="text-xl font-mono text-zinc-100">
            {totalGrossDtao.toFixed(4)}
          </div>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 mb-1">TAO Realized</div>
          <div className="text-xl font-mono text-emerald-400">
            {(totalGrossDtao * 0.842).toFixed(4)}
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
        <h3 className="font-medium text-zinc-50 mb-4">Block Metadata</h3>
        <div className="grid grid-cols-3 gap-6 text-sm">
          <div>
            <div className="text-zinc-500 mb-1">Subnet</div>
            <div className="text-zinc-100">SN1</div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Hotkey</div>
            <div className="text-zinc-100 font-mono text-xs">
              5G9RtsTbiYJJYYqU7UWUJZJYqU7UWU
            </div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Root vs Subnet</div>
            <div className="text-zinc-100">Subnet Emission</div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Total Delegators</div>
            <div className="text-zinc-100">{mockDelegators.length}</div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Validator Commission</div>
            <div className="text-zinc-100">18%</div>
          </div>
          <div>
            <div className="text-zinc-500 mb-1">Attribution Status</div>
            <div className="flex items-center gap-2 text-emerald-400">
              <Check className="h-4 w-4" />
              Complete
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
              <TableHead className="text-zinc-400 text-right">
                Stake Amount
              </TableHead>
              <TableHead className="text-zinc-400">Stake Type</TableHead>
              <TableHead className="text-zinc-400 text-right">
                Proportion
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Gross dTAO
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Validator Retained
              </TableHead>
              <TableHead className="text-zinc-400">
                Partner Attribution
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockDelegators.map((delegator, idx) => (
              <TableRow
                key={idx}
                className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
              >
                <TableCell className="font-mono text-xs text-zinc-300">
                  {delegator.wallet.slice(0, 8)}...{delegator.wallet.slice(-8)}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {delegator.stakeAmount}
                </TableCell>
                <TableCell>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      delegator.stakeType === "TAO"
                        ? "bg-blue-950/50 text-blue-400 border border-blue-900/50"
                        : "bg-purple-950/50 text-purple-400 border border-purple-900/50"
                    }`}
                  >
                    {delegator.stakeType}
                  </span>
                </TableCell>
                <TableCell className="text-right text-zinc-400">
                  {delegator.proportion.toFixed(2)}%
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {delegator.grossDtao}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-400">
                  {delegator.validatorRetained}
                </TableCell>
                <TableCell>
                  {delegator.partnerAttribution ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {delegator.partnerAttribution}
                    </span>
                  ) : (
                    <span className="text-zinc-500 text-sm">None</span>
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
              Sum Check Validated
            </h3>
            <div className="space-y-1 text-sm text-zinc-300">
              <div className="flex justify-between font-mono">
                <span>Sum of delegator attributions:</span>
                <span>{(totalGrossDtao - totalRetained).toFixed(4)} dTAO</span>
              </div>
              <div className="flex justify-between font-mono">
                <span>Validator retained (18%):</span>
                <span>{totalRetained.toFixed(4)} dTAO</span>
              </div>
              <div className="flex justify-between font-mono border-t border-emerald-900/30 pt-1 mt-1">
                <span className="text-emerald-400">Total block yield:</span>
                <span className="text-emerald-400">
                  {totalGrossDtao.toFixed(4)} dTAO
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}