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
  Loader2,
} from "lucide-react";
import { useBlockchain } from "../../hooks/use-blockchain";
import { useState, useEffect } from "react";
import { API_CONFIG, getTaoStatsApiKey, getRpcNodeUrl, getRpcNodeApiKey } from "../../config/api-config";
import { backendService, Partner, RakebackSummary } from "../../services/backend-service";

interface SummaryMetric {
  label: string;
  value: string;
  subtext: string;
}

interface PartnerPerformance {
  name: string;
  type: string;
  rakebackRate: string;
  status: StatusType;
}

export default function SystemOverview() {
  const blockchain = useBlockchain();
  const [taoStatsHealth, setTaoStatsHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [backendHealth, setBackendHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [indexerHealth, setIndexerHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [rpcNodeHealth, setRpcNodeHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");

  const [summaryMetrics, setSummaryMetrics] = useState<SummaryMetric[]>([]);
  const [partnerPerformance, setPartnerPerformance] = useState<PartnerPerformance[]>([]);
  const [financialSummary, setFinancialSummary] = useState<{ totalOwed: string; totalPaid: string; totalOutstanding: string } | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch real data from backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [partners, summary] = await Promise.all([
          backendService.getPartners().catch(() => [] as Partner[]),
          backendService.getRakebackSummary().catch(() => null),
        ]);

        const activePartners = partners.length;
        const totalOwed = summary ? parseFloat(summary.totalTaoOwed) : 0;
        const totalPaid = summary ? parseFloat(summary.totalTaoPaid) : 0;
        const totalOutstanding = summary ? parseFloat(summary.totalTaoOutstanding) : 0;

        setSummaryMetrics([
          {
            label: "Total TAO Owed",
            value: totalOwed > 0 ? `${totalOwed.toLocaleString()} TAO` : "0 TAO",
            subtext: "all time",
          },
          {
            label: "Total TAO Paid",
            value: totalPaid > 0 ? `${totalPaid.toLocaleString()} TAO` : "0 TAO",
            subtext: "all time",
          },
          {
            label: "Active Partners",
            value: String(activePartners),
            subtext: activePartners === 0 ? "none configured" : "configured",
          },
          {
            label: "Outstanding",
            value: totalOutstanding > 0 ? `${totalOutstanding.toLocaleString()} TAO` : "0 TAO",
            subtext: "unpaid balance",
          },
        ]);

        setPartnerPerformance(
          partners.map((p) => ({
            name: p.name,
            type: p.type,
            rakebackRate: `${p.rakebackRate.toFixed(1)}%`,
            status: "active" as StatusType,
          }))
        );

        setFinancialSummary({
          totalOwed: totalOwed > 0 ? `${totalOwed.toLocaleString(undefined, { minimumFractionDigits: 2 })} TAO` : "0 TAO",
          totalPaid: totalPaid > 0 ? `${totalPaid.toLocaleString(undefined, { minimumFractionDigits: 2 })} TAO` : "0 TAO",
          totalOutstanding: totalOutstanding > 0 ? `${totalOutstanding.toLocaleString(undefined, { minimumFractionDigits: 2 })} TAO` : "0 TAO",
        });
      } catch {
        // Graceful fallback — show empty state
        setSummaryMetrics([
          { label: "Total TAO Owed", value: "—", subtext: "backend unavailable" },
          { label: "Total TAO Paid", value: "—", subtext: "backend unavailable" },
          { label: "Active Partners", value: "—", subtext: "backend unavailable" },
          { label: "Outstanding", value: "—", subtext: "backend unavailable" },
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

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

      // Check Backend
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

      // Check RPC node
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

  const getHealthStatusColor = (status: "healthy" | "degraded" | "down" | "disconnected" | "connecting" | "unknown") => {
    switch (status) {
      case "healthy":
        return { icon: CheckCircle2, iconColor: "text-emerald-400", bgColor: "bg-emerald-950/30", borderColor: "border-emerald-900/50" };
      case "degraded":
      case "connecting":
        return { icon: AlertTriangle, iconColor: "text-amber-400", bgColor: "bg-amber-950/30", borderColor: "border-amber-900/50" };
      case "down":
        return { icon: XCircle, iconColor: "text-red-400", bgColor: "bg-red-950/30", borderColor: "border-red-900/50" };
      case "disconnected":
        return { icon: XCircle, iconColor: "text-zinc-500", bgColor: "bg-zinc-900/30", borderColor: "border-zinc-800" };
      default:
        return { icon: AlertCircle, iconColor: "text-zinc-500", bgColor: "bg-zinc-900/30", borderColor: "border-zinc-800" };
    }
  };

  const archiveNodeHealth =
    blockchain.status === "connected"
      ? "healthy"
      : blockchain.status === "error"
        ? "down"
        : blockchain.status === "connecting"
          ? "connecting"
          : "disconnected";

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
        {loading ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 animate-pulse">
              <div className="h-3 bg-zinc-800 rounded w-24 mb-3" />
              <div className="h-7 bg-zinc-800 rounded w-32" />
            </div>
          ))
        ) : (
          summaryMetrics.map((metric, idx) => (
            <div key={idx} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
              <div className="text-xs text-zinc-500 mb-1.5 uppercase tracking-wider">
                {metric.label}
              </div>
              <div className="text-2xl font-semibold text-zinc-50 mb-2">
                {metric.value}
              </div>
              <div className="text-xs text-zinc-500">{metric.subtext}</div>
            </div>
          ))
        )}
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
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">Archive Node</div>
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
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">RPC Node</div>
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
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">TaoStats API</div>
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
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">Backend API</div>
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
                  <div className="text-[11px] text-zinc-500 uppercase tracking-wider">Indexer API</div>
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
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-zinc-400" />
              <h3 className="font-medium text-zinc-50">Rakeback Summary</h3>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {financialSummary ? (
              <>
                <div className="flex justify-between items-baseline">
                  <span className="text-sm text-zinc-400">Total TAO Owed</span>
                  <span className="font-mono text-zinc-100">{financialSummary.totalOwed}</span>
                </div>
                <div className="flex justify-between items-baseline">
                  <span className="text-sm text-zinc-400">Total TAO Paid</span>
                  <span className="font-mono text-emerald-400 font-medium">{financialSummary.totalPaid}</span>
                </div>
                <div className="pt-3 border-t border-zinc-800 flex justify-between items-baseline">
                  <span className="text-sm text-zinc-400 font-medium">Outstanding Balance</span>
                  <span className="font-mono text-amber-400 font-semibold">{financialSummary.totalOutstanding}</span>
                </div>
              </>
            ) : (
              <div className="text-sm text-zinc-500 text-center py-4">No financial data yet</div>
            )}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-zinc-400" />
              <h3 className="font-medium text-zinc-50">Recent Activity</h3>
            </div>
          </div>
          <div className="p-4">
            <div className="text-sm text-zinc-500 text-center py-4">
              No processing data yet. Activity will appear once the pipeline runs.
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
                Configured partners and their rakeback rates
              </p>
            </div>
          </div>
        </div>
        {partnerPerformance.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">
            <Users className="h-8 w-8 mx-auto mb-2 text-zinc-600" />
            <div>No partners configured yet</div>
            <div className="text-sm mt-1">Add partners in the Partner Management page</div>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableHead className="text-zinc-400">Partner</TableHead>
                <TableHead className="text-zinc-400">Type</TableHead>
                <TableHead className="text-zinc-400 text-right">Rakeback Rate</TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {partnerPerformance.map((partner, idx) => (
                <TableRow key={idx} className="border-zinc-800 hover:bg-zinc-800/50">
                  <TableCell className="font-medium text-zinc-100">{partner.name}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {partner.type}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-amber-400">{partner.rakebackRate}</TableCell>
                  <TableCell><StatusBadge status={partner.status} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-950/30 border border-blue-900/50 rounded-lg">
              <Wallet className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Pipeline Status</div>
              <div className="text-xl font-semibold text-zinc-100 mt-0.5">
                {backendHealth === "healthy" ? "Online" : "Offline"}
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
              <div className="text-xs text-zinc-500 uppercase tracking-wider">System Health</div>
              <div className="text-xl font-semibold text-zinc-100 mt-0.5">
                {backendHealth === "healthy" ? "All Systems Go" : "Degraded"}
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
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Pending Settlements</div>
              <div className="text-xl font-semibold text-zinc-100 mt-0.5">
                {financialSummary && parseFloat(financialSummary.totalOutstanding.replace(/[^0-9.]/g, "")) > 0
                  ? financialSummary.totalOutstanding
                  : "0"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
