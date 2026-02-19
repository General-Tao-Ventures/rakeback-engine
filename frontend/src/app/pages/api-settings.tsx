import { useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Settings,
  CheckCircle2,
  XCircle,
  Loader2,
  Database,
  Globe,
  Server,
  Copy,
  ExternalLink,
  AlertCircle,
  Activity,
  AlertTriangle,
  Radio,
} from "lucide-react";
import { toast } from "sonner";
import { useBlockchain } from "../../hooks/use-blockchain";
import { API_CONFIG, getRpcNodeUrl, getRpcNodeApiKey } from "../../config/api-config";
import { blockchainService } from "../../services/blockchain-service";
import { taoStatsService } from "../../services/taostats-service";

export default function ApiSettings() {
  const blockchain = useBlockchain();
  const [isTestingTaoStats, setIsTestingTaoStats] = useState(false);
  const [isTestingBackend, setIsTestingBackend] = useState(false);
  const [isTestingIndexer, setIsTestingIndexer] = useState(false);
  const [isTestingRpcNode, setIsTestingRpcNode] = useState(false);
  const [taoStatsApiKey, setTaoStatsApiKey] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("taostats_api_key");
      if (stored) return stored;
    }
    return API_CONFIG.taoStats.apiKey;
  });
  const [backendUrl, setBackendUrl] = useState(API_CONFIG.backend.baseUrl);
  const [customNodeUrl, setCustomNodeUrl] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("ARCHIVE_NODE_URL");
      if (stored) return stored;
    }
    return API_CONFIG.bittensor.archiveNode;
  });
  const [indexerUrl, setIndexerUrl] = useState("https://api.indexer.bittensor.com");
  const [rpcNodeUrl, setRpcNodeUrl] = useState(() => getRpcNodeUrl());
  const [rpcNodeApiKey, setRpcNodeApiKey] = useState(() => getRpcNodeApiKey());

  // Health status states
  const [archiveNodeHealth, setArchiveNodeHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [rpcNodeHealth, setRpcNodeHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [taoStatsHealth, setTaoStatsHealth] = useState<"healthy" | "degraded" | "down" | "unknown" | "disconnected" | "error">(() => {
    if (typeof window === "undefined") return "unknown";
    const key = localStorage.getItem("taostats_api_key") || API_CONFIG.taoStats.apiKey;
    return key?.trim() ? "unknown" : "disconnected";
  });
  const [backendHealth, setBackendHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");
  const [indexerHealth, setIndexerHealth] = useState<"healthy" | "degraded" | "down" | "unknown">("unknown");

  // Health status helper component
  const HealthIndicator = ({ status }: { status: "healthy" | "degraded" | "down" | "disconnected" | "unknown" | "error" }) => {
    const config = {
      healthy: { color: "text-emerald-400", bg: "bg-emerald-400/10", icon: CheckCircle2, text: "Healthy" },
      degraded: { color: "text-amber-400", bg: "bg-amber-400/10", icon: AlertTriangle, text: "Degraded" },
      down: { color: "text-red-400", bg: "bg-red-400/10", icon: XCircle, text: "Down" },
      error: { color: "text-red-400", bg: "bg-red-400/10", icon: XCircle, text: "Error" },
      disconnected: { color: "text-zinc-500", bg: "bg-zinc-500/10", icon: XCircle, text: "Disconnected" },
      unknown: { color: "text-zinc-500", bg: "bg-zinc-500/10", icon: AlertCircle, text: "Unknown" },
    };

    const { color, bg, icon: Icon, text } = config[status];

    return (
      <div className={`flex items-center gap-1.5 px-2 py-1 rounded ${bg}`}>
        <Icon className={`h-3.5 w-3.5 ${color}`} />
        <span className={`text-xs font-medium ${color}`}>{text}</span>
      </div>
    );
  };

  const handleConnectBlockchain = async () => {
    const url = customNodeUrl?.trim() || API_CONFIG.bittensor.archiveNode;
    try {
      await blockchain.connect(url);
      toast.success(`Connected to: ${blockchainService.getCurrentNodeUrl()}`);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to connect to archive node"
      );
      console.error(error);
    }
  };

  const handleDisconnectBlockchain = async () => {
    await blockchain.disconnect();
    toast.success("Disconnected from archive node");
  };

  const handleTestTaoStats = async () => {
    const keyToTest = taoStatsApiKey?.trim();
    if (!keyToTest) {
      toast.error("Enter an API key before testing");
      setTaoStatsHealth("disconnected");
      return;
    }
    setIsTestingTaoStats(true);
    setTaoStatsHealth("unknown");
    try {
      const result = await taoStatsService.testConnection(keyToTest);

      if (result.ok) {
        localStorage.setItem("taostats_api_key", keyToTest);
        toast.success("TaoStats API connection successful");
        setTaoStatsHealth("healthy");
      } else if (result.status === 401) {
        toast.error("Invalid or missing API key. Check the key and try again.");
        setTaoStatsHealth("error");
      } else {
        toast.error(result.message ? `TaoStats API error: ${result.message}` : `TaoStats API error: ${result.status}`);
        setTaoStatsHealth("error");
      }
    } catch (error) {
      toast.error("Failed to connect to TaoStats API");
      console.error(error);
      setTaoStatsHealth("down");
    } finally {
      setIsTestingTaoStats(false);
    }
  };

  const handleTestBackend = async () => {
    setIsTestingBackend(true);
    try {
      const response = await fetch(`${backendUrl}/health`, {
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        toast.success("Backend API connection successful");
        setBackendHealth("healthy");
      } else {
        toast.error(`Backend API error: ${response.statusText}`);
        setBackendHealth("degraded");
      }
    } catch (error) {
      toast.error("Failed to connect to backend API");
      console.error(error);
      setBackendHealth("down");
    } finally {
      setIsTestingBackend(false);
    }
  };

  const handleTestIndexer = async () => {
    setIsTestingIndexer(true);
    try {
      const response = await fetch(`${indexerUrl}/health`, {
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        toast.success("Indexer API connection successful");
        setIndexerHealth("healthy");
      } else {
        toast.error(`Indexer API error: ${response.statusText}`);
        setIndexerHealth("degraded");
      }
    } catch (error) {
      toast.error("Failed to connect to Indexer API");
      console.error(error);
      setIndexerHealth("down");
    } finally {
      setIsTestingIndexer(false);
    }
  };

  const handleTestRpcNode = async () => {
    setIsTestingRpcNode(true);
    setRpcNodeHealth("unknown");
    try {
      let url = rpcNodeUrl.trim().replace(/\/$/, "");
      const isWs = url.startsWith("ws://") || url.startsWith("wss://");
      if (isWs) {
        toast.info("Use the Bittensor Archive Node section to test WebSocket RPC. This section is for HTTP(S) RPC endpoints.");
        setRpcNodeHealth("unknown");
        return;
      }
      const key = rpcNodeApiKey?.trim();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (key) {
        // dRPC expects Drpc-Key header (or key in URL path)
        headers["Drpc-Key"] = key;
      }
      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify({
          id: 1,
          jsonrpc: "2.0",
          method: "system_health",
          params: [],
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && (data.result !== undefined || data.id === 1)) {
        if (rpcNodeUrl?.trim()) localStorage.setItem("rpc_node_url", rpcNodeUrl.trim());
        if (key) localStorage.setItem("rpc_node_api_key", rpcNodeApiKey.trim());
        toast.success("RPC node connection successful");
        setRpcNodeHealth("healthy");
      } else {
        const err = data.error?.message || data.error || res.statusText;
        toast.error(`RPC node error: ${err || res.status}`);
        setRpcNodeHealth("degraded");
      }
    } catch (error) {
      toast.error("Failed to connect to RPC node");
      console.error(error);
      setRpcNodeHealth("down");
    } finally {
      setIsTestingRpcNode(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          API Configuration
        </h2>
        <p className="text-sm text-zinc-400">
          Configure and test your external API connections and data sources
        </p>
      </div>

      {/* Bittensor Archive Node */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-emerald-400" />
              <h3 className="font-medium text-zinc-50">
                Bittensor Archive Node
              </h3>
            </div>
            <HealthIndicator status={blockchain.status === "connected" ? "healthy" : blockchain.status === "connecting" ? "degraded" : blockchain.status === "error" ? "down" : "disconnected"} />
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time blockchain data from Bittensor network
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Archive Node URL</Label>
            <div className="flex gap-2">
              <Input
                value={customNodeUrl}
                onChange={(e) => setCustomNodeUrl(e.target.value)}
                className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(customNodeUrl)}
                className="bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-zinc-950/50 border border-zinc-800 rounded-lg">
            <div className="flex items-center gap-3">
              {blockchain.status === "connected" && (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              )}
              {blockchain.status === "disconnected" && (
                <XCircle className="h-5 w-5 text-zinc-600" />
              )}
              {blockchain.status === "connecting" && (
                <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
              )}
              {blockchain.status === "error" && (
                <XCircle className="h-5 w-5 text-red-400" />
              )}
              <div>
                <div className="text-sm font-medium text-zinc-200">
                  Status:{" "}
                  {blockchain.status.charAt(0).toUpperCase() +
                    blockchain.status.slice(1)}
                </div>
                {blockchain.currentBlock && (
                  <div className="text-xs text-zinc-500 font-mono">
                    Current Block: {blockchain.currentBlock.toLocaleString()}
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              {blockchain.status === "connected" ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDisconnectBlockchain}
                  className="bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  Disconnect
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={handleConnectBlockchain}
                  disabled={blockchain.status === "connecting"}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {blockchain.status === "connecting" ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    "Connect"
                  )}
                </Button>
              )}
            </div>
          </div>

          <div className="text-xs text-zinc-500 bg-blue-950/20 border border-blue-900/30 rounded p-3">
            <strong className="text-blue-400">Integration Example:</strong> Use{" "}
            <code className="text-blue-300 bg-blue-950/50 px-1 py-0.5 rounded">
              useBlockchain()
            </code>{" "}
            hook to access real-time block data in your components.
          </div>

          <div className="text-xs text-zinc-500 bg-amber-950/20 border border-amber-900/30 rounded p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-amber-400">Important:</strong> If your archive node doesn't have SSL/TLS configured, use{" "}
                <code className="text-amber-300 bg-amber-950/50 px-1 py-0.5 rounded">ws://</code>{" "}
                instead of{" "}
                <code className="text-amber-300 bg-amber-950/50 px-1 py-0.5 rounded">wss://</code>.
                The connection is manual - click "Connect" to establish it.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RPC Node */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="h-5 w-5 text-cyan-400" />
              <h3 className="font-medium text-zinc-50">RPC Node</h3>
            </div>
            <HealthIndicator status={rpcNodeHealth} />
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            HTTP(S) JSON-RPC endpoint for Bittensor (e.g. dRPC, Alchemy). Use for API calls; for live subscriptions use the Archive Node above.
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">RPC Node URL</Label>
            <div className="flex gap-2">
              <Input
                placeholder="https://lb.drpc.live/bittensor/"
                value={rpcNodeUrl}
                onChange={(e) => setRpcNodeUrl(e.target.value)}
                className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(rpcNodeUrl)}
                className="bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-zinc-300">API Key (Optional)</Label>
            <Input
              type="password"
              placeholder="RPC provider API key (e.g. dRPC key)"
              value={rpcNodeApiKey}
              onChange={(e) => setRpcNodeApiKey(e.target.value)}
              className="bg-zinc-900 border-zinc-700 text-zinc-100"
            />
            <p className="text-xs text-zinc-500">
              Some providers (e.g. dRPC) require the key in the URL path or as a header. Stored in{" "}
              <code className="text-zinc-400 bg-zinc-800 px-1 py-0.5 rounded">localStorage</code>; use{" "}
              <code className="text-zinc-400 bg-zinc-800 px-1 py-0.5 rounded">VITE_RPC_NODE_URL</code> /{" "}
              <code className="text-zinc-400 bg-zinc-800 px-1 py-0.5 rounded">VITE_RPC_NODE_API_KEY</code> for production.
            </p>
          </div>

          <Button
            onClick={handleTestRpcNode}
            disabled={isTestingRpcNode}
            className="w-full bg-cyan-600 hover:bg-cyan-700 text-white"
          >
            {isTestingRpcNode ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing Connection...
              </>
            ) : (
              "Test Connection"
            )}
          </Button>

          <div className="text-xs text-zinc-500 bg-cyan-950/20 border border-cyan-900/30 rounded p-3">
            <strong className="text-cyan-400">Usage:</strong> Use{" "}
            <code className="text-cyan-300 bg-cyan-950/50 px-1 py-0.5 rounded">getRpcNodeUrl()</code> and{" "}
            <code className="text-cyan-300 bg-cyan-950/50 px-1 py-0.5 rounded">getRpcNodeApiKey()</code> from{" "}
            <code className="text-cyan-300 bg-cyan-950/50 px-1 py-0.5 rounded">api-config</code> to read the saved RPC node in your app.
          </div>
        </div>
      </div>

      {/* TaoStats API */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-blue-400" />
              <h3 className="font-medium text-zinc-50">TaoStats API</h3>
            </div>
            <div className="flex items-center gap-2">
              <HealthIndicator status={taoStatsHealth} />
              <a
                href="https://taostats.io"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Third-party analytics and statistics for Bittensor network
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Base URL</Label>
            <Input
              value={API_CONFIG.taoStats.baseUrl}
              readOnly
              className="bg-zinc-900 border-zinc-700 text-zinc-100 font-mono text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-zinc-300">API Key (Optional)</Label>
            <Input
              type="password"
              placeholder="Enter your TaoStats API key"
              value={taoStatsApiKey}
              onChange={(e) => setTaoStatsApiKey(e.target.value)}
              className="bg-zinc-900 border-zinc-700 text-zinc-100"
            />
            <p className="text-xs text-zinc-500">
              Set{" "}
              <code className="text-zinc-400 bg-zinc-800 px-1 py-0.5 rounded">
                TAOSTATS_API_KEY
              </code>{" "}
              environment variable for production
            </p>
          </div>

          <Button
            onClick={handleTestTaoStats}
            disabled={isTestingTaoStats}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isTestingTaoStats ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing Connection...
              </>
            ) : (
              "Test Connection"
            )}
          </Button>

          <div className="text-xs text-zinc-500 bg-blue-950/20 border border-blue-900/30 rounded p-3">
            <strong className="text-blue-400">Integration Example:</strong> Use{" "}
            <code className="text-blue-300 bg-blue-950/50 px-1 py-0.5 rounded">
              taoStatsService.getNetworkStats()
            </code>{" "}
            to fetch network statistics.
          </div>
        </div>
      </div>

      {/* Custom Backend API */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5 text-amber-400" />
              <h3 className="font-medium text-zinc-50">Custom Backend API</h3>
            </div>
            <HealthIndicator status={backendHealth} />
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Your custom backend for attribution processing and data storage
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Backend URL</Label>
            <Input
              placeholder="http://localhost:3000"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              className="bg-zinc-900 border-zinc-700 text-zinc-100"
            />
            <p className="text-xs text-zinc-500">
              Set{" "}
              <code className="text-zinc-400 bg-zinc-800 px-1 py-0.5 rounded">
                BACKEND_API_URL
              </code>{" "}
              environment variable for production
            </p>
          </div>

          <Button
            onClick={handleTestBackend}
            disabled={isTestingBackend}
            className="w-full bg-amber-600 hover:bg-amber-700 text-white"
          >
            {isTestingBackend ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing Connection...
              </>
            ) : (
              "Test Connection"
            )}
          </Button>

          <div className="text-xs text-zinc-500 bg-amber-950/20 border border-amber-900/30 rounded p-3">
            <strong className="text-amber-400">Integration Example:</strong> Use{" "}
            <code className="text-amber-300 bg-amber-950/50 px-1 py-0.5 rounded">
              backendService.getPartners()
            </code>{" "}
            to fetch partner data from your backend.
          </div>
        </div>
      </div>

      {/* Indexer API */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-400" />
              <h3 className="font-medium text-zinc-50">Indexer API</h3>
            </div>
            <HealthIndicator status={indexerHealth} />
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Indexer for fast historical blockchain data queries
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Indexer URL</Label>
            <Input
              placeholder="https://api.indexer.bittensor.com"
              value={indexerUrl}
              onChange={(e) => setIndexerUrl(e.target.value)}
              className="bg-zinc-900 border-zinc-700 text-zinc-100"
            />
            <p className="text-xs text-zinc-500">
              Set{" "}
              <code className="text-zinc-400 bg-zinc-800 px-1 py-0.5 rounded">
                INDEXER_API_URL
              </code>{" "}
              environment variable for production
            </p>
          </div>

          <Button
            onClick={handleTestIndexer}
            disabled={isTestingIndexer}
            className="w-full bg-amber-600 hover:bg-amber-700 text-white"
          >
            {isTestingIndexer ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing Connection...
              </>
            ) : (
              "Test Connection"
            )}
          </Button>

          <div className="text-xs text-zinc-500 bg-amber-950/20 border border-amber-900/30 rounded p-3">
            <strong className="text-amber-400">Integration Example:</strong> Use{" "}
            <code className="text-amber-300 bg-amber-950/50 px-1 py-0.5 rounded">
              indexerService.getNetworkStats()
            </code>{" "}
            to fetch network statistics from the indexer.
          </div>
        </div>
      </div>

      {/* Available Endpoints Reference */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-zinc-900/30">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-zinc-400" />
            <h3 className="font-medium text-zinc-50">Quick Reference</h3>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <h4 className="text-sm font-medium text-zinc-300 mb-2">
              RPC Node Config
            </h4>
            <div className="space-y-1 text-xs font-mono text-zinc-500">
              <div>• getRpcNodeUrl() — effective RPC node URL</div>
              <div>• getRpcNodeApiKey() — effective RPC API key</div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-zinc-300 mb-2">
              Blockchain Service Methods
            </h4>
            <div className="space-y-1 text-xs font-mono text-zinc-500">
              <div>• blockchainService.getCurrentBlock()</div>
              <div>• blockchainService.getBlockDetails(blockNumber)</div>
              <div>• blockchainService.getBlockRange(start, end)</div>
              <div>• blockchainService.getStakeForHotkey(hotkey)</div>
              <div>• blockchainService.getDelegatorsForHotkey(hotkey)</div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-zinc-300 mb-2">
              TaoStats Service Methods
            </h4>
            <div className="space-y-1 text-xs font-mono text-zinc-500">
              <div>• taoStatsService.getNetworkStats()</div>
              <div>• taoStatsService.getPrice()</div>
              <div>• taoStatsService.getValidators()</div>
              <div>• taoStatsService.getDelegators()</div>
              <div>• taoStatsService.getSubnets()</div>
              <div>• taoStatsService.getEmissions(params)</div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-zinc-300 mb-2">
              Backend Service Methods
            </h4>
            <div className="space-y-1 text-xs font-mono text-zinc-500">
              <div>• backendService.getPartners()</div>
              <div>• backendService.getAttributions(start, end)</div>
              <div>• backendService.getConversions(params)</div>
              <div>• backendService.getRakebackLedger(partnerId)</div>
              <div>• backendService.exportRakeback(params)</div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-zinc-300 mb-2">
              Indexer Service Methods
            </h4>
            <div className="space-y-1 text-xs font-mono text-zinc-500">
              <div>• indexerService.getNetworkStats()</div>
              <div>• indexerService.getPrice()</div>
              <div>• indexerService.getValidators()</div>
              <div>• indexerService.getDelegators()</div>
              <div>• indexerService.getSubnets()</div>
              <div>• indexerService.getEmissions(params)</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}