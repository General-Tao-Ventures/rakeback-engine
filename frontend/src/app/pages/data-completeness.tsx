import { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { AlertTriangle, AlertCircle, CheckCircle, Clock, Loader2 } from "lucide-react";
import { backendService, CompletenessData } from "../../services/backend-service";

interface DataIssue {
  id: string;
  type: string;
  severity: string;
  description: string;
  affectedBlocks?: string;
  detectedAt: string;
  requiresReview: boolean;
}

interface SystemMetrics {
  blockCoverage: { total: number; complete: number; partial: number; missing: number; percentage: number };
  yieldData: { total: number; complete: number; partial: number; missing: number; percentage: number };
  conversionEvents: { total: number; allocated: number; unallocated: number; percentage: number };
  ledgerEntries: { total: number; complete: number; incomplete: number; percentage: number };
}

interface ActivityEntry {
  timestamp: string;
  event: string;
  details?: string;
  status: string;
}

export default function DataCompleteness() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [issues, setIssues] = useState<DataIssue[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [recentActivity, setRecentActivity] = useState<ActivityEntry[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data: CompletenessData = await backendService.getCompleteness();

        setSystemMetrics(data.systemMetrics);
        setIssues(data.issues);
        setRecentActivity(data.recentActivity);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load completeness data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        <span className="ml-3 text-zinc-400">Loading completeness data...</span>
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

  const metrics = systemMetrics!;

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
            {metrics.blockCoverage.percentage >= 99 ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-400" />
            )}
            <div className="text-xs text-zinc-500">Block Coverage</div>
          </div>
          <div className={`text-2xl font-mono ${metrics.blockCoverage.percentage >= 99 ? "text-emerald-400" : "text-amber-400"}`}>
            {metrics.blockCoverage.total > 0 ? `${metrics.blockCoverage.percentage.toFixed(3)}%` : "—"}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {metrics.blockCoverage.complete.toLocaleString()} / {metrics.blockCoverage.total.toLocaleString()}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            {metrics.yieldData.percentage >= 99 ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-400" />
            )}
            <div className="text-xs text-zinc-500">Yield Data</div>
          </div>
          <div className={`text-2xl font-mono ${metrics.yieldData.percentage >= 99 ? "text-emerald-400" : "text-amber-400"}`}>
            {metrics.yieldData.total > 0 ? `${metrics.yieldData.percentage.toFixed(3)}%` : "—"}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {metrics.yieldData.complete.toLocaleString()} / {metrics.yieldData.total.toLocaleString()}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            {metrics.conversionEvents.percentage >= 99 ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-400" />
            )}
            <div className="text-xs text-zinc-500">Conversions</div>
          </div>
          <div className={`text-2xl font-mono ${metrics.conversionEvents.percentage >= 99 ? "text-emerald-400" : "text-amber-400"}`}>
            {metrics.conversionEvents.total > 0 ? `${metrics.conversionEvents.percentage.toFixed(3)}%` : "—"}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {metrics.conversionEvents.allocated.toLocaleString()} / {metrics.conversionEvents.total.toLocaleString()}
          </div>
        </div>

        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            {metrics.ledgerEntries.percentage >= 99 ? (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-400" />
            )}
            <div className="text-xs text-zinc-500">Ledger Entries</div>
          </div>
          <div className={`text-2xl font-mono ${metrics.ledgerEntries.percentage >= 99 ? "text-emerald-400" : "text-amber-400"}`}>
            {metrics.ledgerEntries.total > 0 ? `${metrics.ledgerEntries.percentage.toFixed(1)}%` : "—"}
          </div>
          <div className="text-xs text-zinc-500 mt-1">
            {metrics.ledgerEntries.complete.toLocaleString()} / {metrics.ledgerEntries.total.toLocaleString()}
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
              {issues.filter((i) => i.requiresReview).length} require review
            </span>
          </div>
        </div>

        {issues.length > 0 ? (
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
              {issues.map((issue) => (
                <TableRow
                  key={issue.id}
                  className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                >
                  <TableCell className="font-mono text-sm text-zinc-300">
                    {issue.id.slice(0, 12)}
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
                  <TableCell className="text-zinc-300">{issue.description}</TableCell>
                  <TableCell className="text-zinc-400 text-sm">
                    {issue.affectedBlocks && (
                      <div className="font-mono">Blocks: {issue.affectedBlocks}</div>
                    )}
                  </TableCell>
                  <TableCell className="text-zinc-400 text-sm">{issue.detectedAt}</TableCell>
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
        {recentActivity.length > 0 ? (
          <div className="divide-y divide-zinc-800">
            {recentActivity.map((activity, idx) => (
              <div key={idx} className="p-4 hover:bg-zinc-800/30 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="flex-shrink-0 mt-0.5">
                      {activity.status === "success" && <CheckCircle className="h-4 w-4 text-emerald-400" />}
                      {activity.status === "warning" && <AlertCircle className="h-4 w-4 text-amber-400" />}
                      {activity.status === "error" && <AlertTriangle className="h-4 w-4 text-red-400" />}
                      {activity.status === "info" && <AlertCircle className="h-4 w-4 text-blue-400" />}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm text-zinc-100">{activity.event}</div>
                      {activity.details && (
                        <div className="text-xs text-zinc-500 mt-0.5 font-mono">{activity.details}</div>
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
        ) : (
          <div className="p-8 text-center text-zinc-500">
            <div>No processing activity yet</div>
            <div className="text-sm mt-1">Activity will appear once the pipeline runs</div>
          </div>
        )}
      </div>

      {/* System Guarantees */}
      <div className="bg-zinc-900/30 border border-zinc-800 rounded-lg p-6">
        <h3 className="font-medium text-zinc-50 mb-4">
          Data Quality Guarantees
        </h3>
        <div className="grid grid-cols-2 gap-6 text-sm">
          <div>
            <div className="text-emerald-400 mb-1">No Auto-Hiding</div>
            <div className="text-zinc-400">
              All data issues are permanently visible until manually resolved
            </div>
          </div>
          <div>
            <div className="text-emerald-400 mb-1">Immutable Logs</div>
            <div className="text-zinc-400">
              Activity logs are append-only and cannot be deleted or modified
            </div>
          </div>
          <div>
            <div className="text-emerald-400 mb-1">Proactive Alerting</div>
            <div className="text-zinc-400">
              Missing data detected within one block cycle (~12 seconds)
            </div>
          </div>
          <div>
            <div className="text-emerald-400 mb-1">Coverage Metrics</div>
            <div className="text-zinc-400">
              Real-time completeness percentages for all critical data types
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
