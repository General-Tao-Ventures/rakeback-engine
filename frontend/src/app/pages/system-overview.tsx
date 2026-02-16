import { StatusBadge, StatusType } from "../components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  Users,
  DollarSign,
  Activity,
  AlertCircle,
  CheckCircle2,
  Database,
  Globe,
  Server,
  XCircle,
  AlertTriangle,
  Radio,
} from "lucide-react";
import { useBlockchain } from "../../hooks/use-blockchain";
import { useState, useEffect } from "react";
import { API_CONFIG, getTaoStatsApiKey, getRpcNodeUrl, getRpcNodeApiKey } from "../../config/api-config";

// Summary metrics
const summaryMetrics = [
  {
    label: "Total Rakeback (MTD)",
    value: "1,847.32 TAO",
    change: "+12.4%",
    trend: "up" as const,
    subtext: "vs last month",
  },
  {
    label: "Total Rakeback (YTD)",
    value: "18,392.58 TAO",
    change: "+24.8%",
    trend: "up" as const,
    subtext: "vs last year",
  },
  {
    label: "Active Partners",
    value: "2",
    change: "0",
    trend: "neutral" as const,
    subtext: "no change",
  },
  {
    label: "Tracked Wallets",
    value: "1,247",
    change: "+89",
    trend: "up" as const,
    subtext: "this month",
  },
];

// Partner performance
interface PartnerPerformance {
  name: string;
  type: string;
  rakebackMTD: string;
  rakebackYTD: string;
  walletCount: number;
  avgYieldPerWallet: string;
  status: StatusType;
}

const partnerPerformance: PartnerPerformance[] = [
  {
    name: "Creative Builds",
    type: "Named",
    rakebackMTD: "1,124.85 TAO",
    rakebackYTD: "11,523.44 TAO",
    walletCount: 1,
    avgYieldPerWallet: "1,124.85 TAO",
    status: "active",
  },
  {
    name: "Talisman",
    type: "Tag-based",
    rakebackMTD: "722.47 TAO",
    rakebackYTD: "6,869.14 TAO",
    walletCount: 1246,
    avgYieldPerWallet: "0.58 TAO",
    status: "active",
  },
];

// Recent activity
interface RecentActivity {
  timestamp: string;
  type: string;
  partner: string;
  amount: string;
  blockRange: string;
  status: StatusType;
}

const recentActivity: RecentActivity[] = [
  {
    timestamp: "2026-02-14 08:15:00",
    type: "Daily Settlement",
    partner: "Creative Builds",
    amount: "47.23 TAO",
    blockRange: "4,520,100 - 4,527,200",
    status: "complete",
  },
  {
    timestamp: "2026-02-14 08:15:00",
    type: "Daily Settlement",
    partner: "Talisman",
    amount: "28.94 TAO",
    blockRange: "4,520,100 - 4,527,200",
    status: "complete",
  },
  {
    timestamp: "2026-02-13 08:10:00",
    type: "Daily Settlement",
    partner: "Creative Builds",
    amount: "51.18 TAO",
    blockRange: "4,512,900 - 4,520,099",
    status: "complete",
  },
  {
    timestamp: "2026-02-13 08:10:00",
    type: "Daily Settlement",
    partner: "Talisman",
    amount: "31.22 TAO",
    blockRange: "4,512,900 - 4,520,099",
    status: "complete",
  },
  {
    timestamp: "2026-02-12 08:05:00",
    type: "Daily Settlement",
    partner: "Creative Builds",
    amount: "49.67 TAO",
    blockRange: "4,505,700 - 4,512,899",
    status: "complete",
  },
];

// System health
interface SystemHealth {
  component: string;
  status: StatusType;
  lastUpdate: string;
  metric: string;
}

const systemHealth: SystemHealth[] = [
  {
    component: "Block Ingestion",
    status: "active",
    lastUpdate: "2026-02-14 09:47:12",
    metric: "Block 4,527,342 (12s ago)",
  },
  {
    component: "Attribution Engine",
    status: "active",
    lastUpdate: "2026-02-14 09:47:08",
    metric: "Processing block 4,527,341",
  },
  {
    component: "Conversion Tracker",
    status: "active",
    lastUpdate: "2026-02-14 09:47:05",
    metric: "Last conversion: block 4,527,289",
  },
  {
    component: "Partner Ledger",
    status: "active",
    lastUpdate: "2026-02-14 08:15:00",
    metric: "Daily settlement complete",
  },
];

// Financial summary
const financialSummary = {
  currentMonth: {
    totalYield: "12,315.47 TAO",
    totalRakeback: "1,847.32 TAO",
    rakebackRate: "15.0%",
    netYield: "10,468.15 TAO",
  },
  yearToDate: {
    totalYield: "122,617.20 TAO",
    totalRakeback: "18,392.58 TAO",
    rakebackRate: "15.0%",
    netYield: "104,224.62 TAO",
  },
};

export default function SystemOverview() {
  const blockchain = useBlockchain();
  const [taoStatsHealth, setTaoStatsHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [backendHealth, setBackendHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [indexerHealth, setIndexerHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [rpcNodeHealth, setRpcNodeHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");

  // Check API health on mount
  useEffect(() => {
    const checkApiHealth = async () => {
      // Check TaoStats
      try {
        const taoStatsKey = getTaoStatsApiKey();
        const taoStatsResponse = await fetch(`${API_CONFIG.taoStats.baseUrl}${API_CONFIG.taoStats.endpoints.network}`, {
          headers: {
            "Content-Type": "application/json",
            ...(taoStatsKey && { "x-api-key": taoStatsKey }),
          },
        });
        setTaoStatsHealth(taoStatsResponse.ok ? "healthy" : "degraded");
      } catch {
        setTaoStatsHealth("down");
      }

      // Check Backend (will fail for now since it's not set up)
      try {
        const backendResponse = await fetch(`${API_CONFIG.backend.baseUrl}/health`, {
          headers: { "Content-Type": "application/json" },
        });
        setBackendHealth(backendResponse.ok ? "healthy" : "degraded");
      } catch {
        setBackendHealth("down");
      }

      // Check Indexer (placeholder)
      setIndexerHealth("unknown");

      // Check RPC node (HTTP JSON-RPC; dRPC uses Drpc-Key header)
      try {
        const rpcUrl = getRpcNodeUrl();
        const rpcKey = getRpcNodeApiKey();
        const rpcResponse = await fetch(rpcUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(rpcKey && { "Drpc-Key": rpcKey }),
          },
          body: JSON.stringify({
            jsonrpc: "2.0",
            method: "system_health",
            params: [],
            id: 1,
          }),
        });
        const data = await rpcResponse.json().catch(() => ({}));
        setRpcNodeHealth(rpcResponse.ok && data.result != null ? "healthy" : "degraded");
      } catch {
        setRpcNodeHealth("down");
      }
    };

    checkApiHealth();
  }, []);

  const getHealthStatusColor = (status: "healthy" | "degraded" | "down" | "unknown") => {
    switch (status) {
      case "healthy":
        return { icon: CheckCircle2, iconColor: "text-emerald-400", bgColor: "bg-emerald-950/30", borderColor: "border-emerald-900/50" };
      case "degraded":
        return { icon: AlertTriangle, iconColor: "text-amber-400", bgColor: "bg-amber-950/30", borderColor: "border-amber-900/50" };
      case "down":
        return { icon: XCircle, iconColor: "text-red-400", bgColor: "bg-red-950/30", borderColor: "border-red-900/50" };
      default:
        return { icon: AlertCircle, iconColor: "text-zinc-500", bgColor: "bg-zinc-900/30", borderColor: "border-zinc-800" };
    }
  };

  const archiveNodeHealth = blockchain.status === "connected" ? "healthy" : blockchain.status === "error" ? "down" : "unknown";

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Rakeback Dashboard
        </h2>
        <p className="text-sm text-zinc-400">
          Real-time rakeback performance, partner metrics, and system health
        </p>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-4 gap-4">
        {summaryMetrics.map((metric, idx) => (
          <div
            key={idx}
            className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4"
          >
            <div className="text-xs text-zinc-500 mb-1.5 uppercase tracking-wider">
              {metric.label}
            </div>
            <div className="text-2xl font-semibold text-zinc-50 mb-2">
              {metric.value}
            </div>
            <div className="flex items-center gap-2 text-xs">
              {metric.trend === "up" && (
                <div className="flex items-center gap-1 text-emerald-400">
                  <TrendingUp className="h-3 w-3" />
                  <span>{metric.change}</span>
                </div>
              )}
              {metric.trend === "down" && (
                <div className="flex items-center gap-1 text-red-400">
                  <TrendingDown className="h-3 w-3" />
                  <span>{metric.change}</span>
                </div>
              )}
              {metric.trend === "neutral" && (
                <div className="text-zinc-500">{metric.change}</div>
              )}
              <span className="text-zinc-500">{metric.subtext}</span>
            </div>
          </div>
        ))}
      </div>

      {/* API Health Status */}
      <div className="grid grid-cols-5 gap-3">
        {/* Archive Node */}
        {(() => {
          const healthStatus = getHealthStatusColor(archiveNodeHealth);
          return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 ${healthStatus.bgColor} border ${healthStatus.borderColor} rounded-lg shrink-0`}>
                  <Database className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">
                    Archive Node
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <healthStatus.icon className={`h-3.5 w-3.5 ${healthStatus.iconColor}`} />
                    <span className={`text-xs font-medium ${healthStatus.iconColor}`}>
                      {archiveNodeHealth.charAt(0).toUpperCase() + archiveNodeHealth.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* RPC Node */}
        {(() => {
          const healthStatus = getHealthStatusColor(rpcNodeHealth);
          return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 ${healthStatus.bgColor} border ${healthStatus.borderColor} rounded-lg shrink-0`}>
                  <Radio className="h-4 w-4 text-cyan-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">
                    RPC Node
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <healthStatus.icon className={`h-3.5 w-3.5 ${healthStatus.iconColor}`} />
                    <span className={`text-xs font-medium ${healthStatus.iconColor}`}>
                      {rpcNodeHealth.charAt(0).toUpperCase() + rpcNodeHealth.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* TaoStats API */}
        {(() => {
          const healthStatus = getHealthStatusColor(taoStatsHealth);
          return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 ${healthStatus.bgColor} border ${healthStatus.borderColor} rounded-lg shrink-0`}>
                  <Globe className="h-4 w-4 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">
                    TaoStats API
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <healthStatus.icon className={`h-3.5 w-3.5 ${healthStatus.iconColor}`} />
                    <span className={`text-xs font-medium ${healthStatus.iconColor}`}>
                      {taoStatsHealth.charAt(0).toUpperCase() + taoStatsHealth.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Backend API */}
        {(() => {
          const healthStatus = getHealthStatusColor(backendHealth);
          return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 ${healthStatus.bgColor} border ${healthStatus.borderColor} rounded-lg shrink-0`}>
                  <Server className="h-4 w-4 text-amber-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">
                    Backend API
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <healthStatus.icon className={`h-3.5 w-3.5 ${healthStatus.iconColor}`} />
                    <span className={`text-xs font-medium ${healthStatus.iconColor}`}>
                      {backendHealth.charAt(0).toUpperCase() + backendHealth.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Indexer API */}
        {(() => {
          const healthStatus = getHealthStatusColor(indexerHealth);
          return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center gap-2.5">
                <div className={`p-1.5 ${healthStatus.bgColor} border ${healthStatus.borderColor} rounded-lg shrink-0`}>
                  <Activity className="h-4 w-4 text-purple-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">
                    Indexer API
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <healthStatus.icon className={`h-3.5 w-3.5 ${healthStatus.iconColor}`} />
                    <span className={`text-xs font-medium ${healthStatus.iconColor}`}>
                      {indexerHealth.charAt(0).toUpperCase() + indexerHealth.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}
      </div>

      {/* Financial Summary */}
      <div className="grid grid-cols-2 gap-4">
        {/* Current Month */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-zinc-400" />
              <h3 className="font-medium text-zinc-50">
                February 2026 (Month-to-Date)
              </h3>
            </div>
          </div>
          <div className="p-4 space-y-3">
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-zinc-400">Total Yield</span>
              <span className="font-mono text-zinc-100">
                {financialSummary.currentMonth.totalYield}
              </span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-zinc-400">Total Rakeback</span>
              <span className="font-mono text-amber-400 font-medium">
                {financialSummary.currentMonth.totalRakeback}
              </span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-zinc-400">Effective Rate</span>
              <span className="font-mono text-zinc-300">
                {financialSummary.currentMonth.rakebackRate}
              </span>
            </div>
            <div className="pt-3 border-t border-zinc-800 flex justify-between items-baseline">
              <span className="text-sm text-zinc-400 font-medium">
                Net Yield (After Rakeback)
              </span>
              <span className="font-mono text-emerald-400 font-semibold">
                {financialSummary.currentMonth.netYield}
              </span>
            </div>
          </div>
        </div>

        {/* Year to Date */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-zinc-400" />
              <h3 className="font-medium text-zinc-50">2026 (Year-to-Date)</h3>
            </div>
          </div>
          <div className="p-4 space-y-3">
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-zinc-400">Total Yield</span>
              <span className="font-mono text-zinc-100">
                {financialSummary.yearToDate.totalYield}
              </span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-zinc-400">Total Rakeback</span>
              <span className="font-mono text-amber-400 font-medium">
                {financialSummary.yearToDate.totalRakeback}
              </span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-zinc-400">Effective Rate</span>
              <span className="font-mono text-zinc-300">
                {financialSummary.yearToDate.rakebackRate}
              </span>
            </div>
            <div className="pt-3 border-t border-zinc-800 flex justify-between items-baseline">
              <span className="text-sm text-zinc-400 font-medium">
                Net Yield (After Rakeback)
              </span>
              <span className="font-mono text-emerald-400 font-semibold">
                {financialSummary.yearToDate.netYield}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Partner Performance */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-zinc-400" />
            <div>
              <h3 className="font-medium text-zinc-50">Partner Performance</h3>
              <p className="text-sm text-zinc-400 mt-0.5">
                Rakeback metrics by partner
              </p>
            </div>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Partner</TableHead>
              <TableHead className="text-zinc-400">Type</TableHead>
              <TableHead className="text-zinc-400 text-right">
                Rakeback MTD
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Rakeback YTD
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Wallets
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Avg Yield/Wallet
              </TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {partnerPerformance.map((partner, idx) => (
              <TableRow
                key={idx}
                className="border-zinc-800 hover:bg-zinc-800/50"
              >
                <TableCell className="font-medium text-zinc-100">
                  {partner.name}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                    {partner.type}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-amber-400">
                  {partner.rakebackMTD}
                </TableCell>
                <TableCell className="text-right font-mono text-amber-400">
                  {partner.rakebackYTD}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-300">
                  {partner.walletCount.toLocaleString()}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-400 text-sm">
                  {partner.avgYieldPerWallet}
                </TableCell>
                <TableCell>
                  <StatusBadge status={partner.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Recent Activity */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-zinc-400" />
            <div>
              <h3 className="font-medium text-zinc-50">Recent Activity</h3>
              <p className="text-sm text-zinc-400 mt-0.5">
                Latest settlements and transactions
              </p>
            </div>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Timestamp</TableHead>
              <TableHead className="text-zinc-400">Type</TableHead>
              <TableHead className="text-zinc-400">Partner</TableHead>
              <TableHead className="text-zinc-400 text-right">Amount</TableHead>
              <TableHead className="text-zinc-400">Block Range</TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recentActivity.map((activity, idx) => (
              <TableRow
                key={idx}
                className="border-zinc-800 hover:bg-zinc-800/50"
              >
                <TableCell className="text-zinc-400 text-sm font-mono">
                  {activity.timestamp}
                </TableCell>
                <TableCell className="text-zinc-300 text-sm">
                  {activity.type}
                </TableCell>
                <TableCell className="text-zinc-100 font-medium">
                  {activity.partner}
                </TableCell>
                <TableCell className="text-right font-mono text-emerald-400">
                  {activity.amount}
                </TableCell>
                <TableCell className="font-mono text-zinc-400 text-sm">
                  {activity.blockRange}
                </TableCell>
                <TableCell>
                  <StatusBadge status={activity.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* System Health */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            <div>
              <h3 className="font-medium text-zinc-50">System Health</h3>
              <p className="text-sm text-zinc-400 mt-0.5">
                Real-time status of all pipeline components
              </p>
            </div>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Component</TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
              <TableHead className="text-zinc-400">Last Update</TableHead>
              <TableHead className="text-zinc-400">Current Metric</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {systemHealth.map((component, idx) => (
              <TableRow
                key={idx}
                className="border-zinc-800 hover:bg-zinc-800/50"
              >
                <TableCell className="font-medium text-zinc-100">
                  {component.component}
                </TableCell>
                <TableCell>
                  <StatusBadge status={component.status} />
                </TableCell>
                <TableCell className="font-mono text-zinc-400 text-sm">
                  {component.lastUpdate}
                </TableCell>
                <TableCell className="text-zinc-300 text-sm">
                  {component.metric}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-950/30 border border-blue-900/50 rounded-lg">
              <Wallet className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">
                Avg Daily Rakeback
              </div>
              <div className="text-xl font-semibold text-zinc-100 mt-0.5">
                131.95 TAO
              </div>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-950/30 border border-emerald-900/50 rounded-lg">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">
                Blocks Processed (24h)
              </div>
              <div className="text-xl font-semibold text-zinc-100 mt-0.5">
                7,200
              </div>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-950/30 border border-amber-900/50 rounded-lg">
              <AlertCircle className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">
                Pending Settlements
              </div>
              <div className="text-xl font-semibold text-zinc-100 mt-0.5">
                0
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}