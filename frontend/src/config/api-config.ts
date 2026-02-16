/**
 * API Configuration
 * 
 * Configure your external API endpoints and keys here.
 * For production, use environment variables instead of hardcoded values.
 */

export const API_CONFIG = {
  // Bittensor Archive Node
  bittensor: {
    // Try ws:// if wss:// fails (SSL issues)
    archiveNode: "ws://185.189.45.20:9944",
    // Alternative: use wss:// if SSL is configured
    // archiveNode: "wss://185.189.45.20:9944",
    
    // Alternative nodes for fallback
    fallbackNodes: [
      "wss://entrypoint-finney.opentensor.ai:443",
      "wss://archive.chain.opentensor.ai:443",
    ],
    
    // Connection options
    connectionTimeout: 30000, // 30 seconds
    maxRetries: 3,
    retryDelay: 2000, // 2 seconds
  },

  // RPC Node (HTTP/HTTPS JSON-RPC, e.g. dRPC, Alchemy – use for API calls)
  rpcNode: {
    url: (import.meta.env?.VITE_RPC_NODE_URL as string) || "https://lb.drpc.live/bittensor/",
    apiKey: (import.meta.env?.VITE_RPC_NODE_API_KEY as string) || "",
  },

  // TaoStats API (use VITE_TAOSTATS_API_KEY in .env for dev)
  taoStats: {
    baseUrl: "https://api.taostats.io",
    apiKey: (import.meta.env?.VITE_TAOSTATS_API_KEY as string) || "",
    endpoints: {
      validators: "/validators",
      delegators: "/delegators",
      subnets: "/subnets",
      network: "/api/stats/latest/v1",
      emissions: "/emissions",
      price: "/api/price/latest/v1",
    },
  },

  // Custom Backend API (use VITE_BACKEND_API_URL in .env to override)
  backend: {
    baseUrl: (import.meta.env?.VITE_BACKEND_API_URL as string) || "http://localhost:8000",
    endpoints: {
      partners: "/api/partners",
      attributions: "/api/attributions",
      conversions: "/api/conversions",
      rakeback: "/api/rakeback",
      exports: "/api/exports",
    },
  },
};

/** Get effective TaoStats API key: localStorage (saved in API settings) then env */
export const getTaoStatsApiKey = (): string => {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("taostats_api_key");
    if (stored) return stored;
  }
  return (import.meta.env?.VITE_TAOSTATS_API_KEY as string) || "";
};

/** Get effective RPC node URL: localStorage (saved in API settings) then env then default */
export const getRpcNodeUrl = (): string => {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("rpc_node_url");
    if (stored) return stored;
  }
  return (import.meta.env?.VITE_RPC_NODE_URL as string) || API_CONFIG.rpcNode.url;
};

/** Get effective RPC node API key: localStorage (saved in API settings) then env */
export const getRpcNodeApiKey = (): string => {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("rpc_node_api_key");
    if (stored) return stored;
  }
  return (import.meta.env?.VITE_RPC_NODE_API_KEY as string) || API_CONFIG.rpcNode.apiKey;
};

// API Request Headers
export const getApiHeaders = (apiKey?: string) => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const key = apiKey ?? getTaoStatsApiKey();
  if (key) {
    // TaoStats uses x-api-key header (not Bearer)
    headers["x-api-key"] = key;
  }

  return headers;
};