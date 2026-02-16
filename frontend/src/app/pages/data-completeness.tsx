import { StatusBadge } from "../components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { AlertTriangle, AlertCircle, CheckCircle, Clock } from "lucide-react";

interface DataIssue {
  id: string;
  type: "missing-block" | "missing-yield" | "missing-conversion" | "incomplete-ledger";
  severity: "critical" | "warning" | "info";
  description: string;
  affectedBlocks?: string;
  affectedSubnet?: string;
  detectedAt: string;
  requiresReview: boolean;
}

const mockIssues: DataIssue[] = [
  {
    id: "ISS-2026-02-14-003",
    type: "missing-block",
    severity: "critical",
    description: "Block snapshot missing for block 4521887",
    affectedBlocks: "4521887",
    affectedSubnet: "ROOT",
    detectedAt: "2026-02-14 08:25:00",
    requiresReview: true,
  },
  {
    id: "ISS-2026-02-14-002",
    type: "missing-yield",
    severity: "warning",
    description: "Partial yield data for block range 4521890-4521892",
    affectedBlocks: "4521890-4521892",
    affectedSubnet: "SN8",
    detectedAt: "2026-02-14 08:23:30",
    requiresReview: true,
  },
  {
    id: "ISS-2026-02-13-001",
    type: "missing-conversion",
    severity: "warning",
    description: "Conversion event CVT-2026-02-12-001 not fully allocated",
    affectedSubnet: "ROOT",
    detectedAt: "2026-02-13 16:45:00",
    requiresReview: true,
  },
];

const systemMetrics = {
  blockCoverage: {
    total: 100000,
    complete: 99894,
    partial: 103,
    missing: 3,
    percentage: 99.894,
  },
  yieldData: {
    total: 98432,
    complete: 98329,
    partial: 101,
    missing: 2,
    percentage: 99.895,
  },
  conversionEvents: {
    total: 156,
    allocated: 154,
    partiallyAllocated: 1,
    unallocated: 1,
    percentage: 98.718,
  },
  ledgerEntries: {
    total: 48,
    complete: 48,
    incomplete: 0,
    percentage: 100.0,
  },
};

const recentActivity = [
  {
    timestamp: "2026-02-14 10:32:15",
    event: "Block ingestion completed",
    blocks: "4521893-4521900",
    status: "success",
  },
  {
    timestamp: "2026-02-14 10:30:45",
    event: "Conversion allocation completed",
    details: "CVT-2026-02-14-001",
    status: "success",
  },
  {
    timestamp: "2026-02-14 10:28:20",
    event: "Partner attribution updated",
    details: "Creative Builds, Talisman",
    status: "success",
  },
  {
    timestamp: "2026-02-14 08:25:00",
    event: "Missing block snapshot detected",
    details: "Block 4521887 (ROOT)",
    status: "error",
  },
  {
    timestamp: "2026-02-14 08:23:30",
    event: "Partial yield data detected",
    details: "Blocks 4521890-4521892 (SN8)",
    status: "warning",
  },
];

export default function DataCompleteness() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Data Completeness & Alerts
        </h2>
        <p className="text-sm text-zinc-400">
          Operational confidence through transparent data quality monitoring
        </p>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <div className="text-xs text-zinc-500">Block Coverage</div>
          </div>
          <div className="text-2xl font-mono text-emerald-400">
            {systemMetrics.blockCoverage.percentage.toFixed(3)}%
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {systemMetrics.blockCoverage.complete.toLocaleString()} /{" "}
            {systemMetrics.blockCoverage.total.toLocaleString()}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <div className="text-xs text-zinc-500">Yield Data</div>
          </div>
          <div className="text-2xl font-mono text-emerald-400">
            {systemMetrics.yieldData.percentage.toFixed(3)}%
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {systemMetrics.yieldData.complete.toLocaleString()} /{" "}
            {systemMetrics.yieldData.total.toLocaleString()}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-4 w-4 text-amber-400" />
            <div className="text-xs text-zinc-500">Conversions</div>
          </div>
          <div className="text-2xl font-mono text-amber-400">
            {systemMetrics.conversionEvents.percentage.toFixed(3)}%
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {systemMetrics.conversionEvents.allocated.toLocaleString()} /{" "}
            {systemMetrics.conversionEvents.total.toLocaleString()}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <div className="text-xs text-zinc-500">Ledger Entries</div>
          </div>
          <div className="text-2xl font-mono text-emerald-400">
            {systemMetrics.ledgerEntries.percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {systemMetrics.ledgerEntries.complete.toLocaleString()} /{" "}
            {systemMetrics.ledgerEntries.total.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Active Issues */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h3 className="font-medium text-zinc-50">Active Issues</h3>
            <p className="text-sm text-zinc-400 mt-1">
              Data quality issues requiring review or intervention
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-500">
              {mockIssues.filter((i) => i.requiresReview).length} require review
            </span>
          </div>
        </div>

        {mockIssues.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
                <TableHead className="text-zinc-400">Issue ID</TableHead>
                <TableHead className="text-zinc-400">Type</TableHead>
                <TableHead className="text-zinc-400">Severity</TableHead>
                <TableHead className="text-zinc-400">Description</TableHead>
                <TableHead className="text-zinc-400">Affected</TableHead>
                <TableHead className="text-zinc-400">Detected At</TableHead>
                <TableHead className="text-zinc-400">Review Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockIssues.map((issue) => (
                <TableRow
                  key={issue.id}
                  className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                >
                  <TableCell className="font-mono text-sm text-zinc-300">
                    {issue.id}
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {issue.type}
                    </span>
                  </TableCell>
                  <TableCell>
                    {issue.severity === "critical" && (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-red-950/50 text-red-400 border border-red-900/50">
                        <AlertTriangle className="h-3 w-3" />
                        Critical
                      </span>
                    )}
                    {issue.severity === "warning" && (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-amber-950/50 text-amber-400 border border-amber-900/50">
                        <AlertCircle className="h-3 w-3" />
                        Warning
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-zinc-300">
                    {issue.description}
                  </TableCell>
                  <TableCell className="text-zinc-400 text-sm">
                    {issue.affectedBlocks && (
                      <div className="font-mono">Blocks: {issue.affectedBlocks}</div>
                    )}
                    {issue.affectedSubnet && (
                      <div>Subnet: {issue.affectedSubnet}</div>
                    )}
                  </TableCell>
                  <TableCell className="text-zinc-400 text-sm">
                    {issue.detectedAt}
                  </TableCell>
                  <TableCell>
                    {issue.requiresReview ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-amber-950/50 text-amber-400 border border-amber-900/50">
                        <AlertCircle className="h-3 w-3" />
                        Requires Review
                      </span>
                    ) : (
                      <span className="text-zinc-500 text-sm">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="p-8 text-center text-zinc-500">
            <CheckCircle className="h-12 w-12 mx-auto mb-3 text-emerald-400" />
            <div className="text-emerald-400">No active issues</div>
            <div className="text-sm mt-1">All systems operational</div>
          </div>
        )}
      </div>

      {/* Recent Activity Log */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h3 className="font-medium text-zinc-50">Recent Activity</h3>
          <p className="text-sm text-zinc-400 mt-1">
            System events and processing timeline
          </p>
        </div>
        <div className="divide-y divide-zinc-800">
          {recentActivity.map((activity, idx) => (
            <div
              key={idx}
              className="p-4 hover:bg-zinc-800/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <div className="flex-shrink-0 mt-0.5">
                    {activity.status === "success" && (
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                    )}
                    {activity.status === "warning" && (
                      <AlertCircle className="h-4 w-4 text-amber-400" />
                    )}
                    {activity.status === "error" && (
                      <AlertTriangle className="h-4 w-4 text-red-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-zinc-100">{activity.event}</div>
                    {(activity.blocks || activity.details) && (
                      <div className="text-xs text-zinc-500 mt-0.5 font-mono">
                        {activity.blocks || activity.details}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <Clock className="h-3 w-3" />
                  {activity.timestamp}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Guarantees */}
      <div className="bg-zinc-900/30 border border-zinc-800 rounded-lg p-6">
        <h3 className="font-medium text-zinc-50 mb-4">
          Data Quality Guarantees
        </h3>
        <div className="grid grid-cols-2 gap-6 text-sm">
          <div>
            <div className="text-emerald-400 mb-1">✓ No Auto-Hiding</div>
            <div className="text-zinc-400">
              All data issues are permanently visible until manually resolved
            </div>
          </div>
          <div>
            <div className="text-emerald-400 mb-1">✓ Immutable Logs</div>
            <div className="text-zinc-400">
              Activity logs are append-only and cannot be deleted or modified
            </div>
          </div>
          <div>
            <div className="text-emerald-400 mb-1">✓ Proactive Alerting</div>
            <div className="text-zinc-400">
              Missing data detected within one block cycle (~12 seconds)
            </div>
          </div>
          <div>
            <div className="text-emerald-400 mb-1">✓ Coverage Metrics</div>
            <div className="text-zinc-400">
              Real-time completeness percentages for all critical data types
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}