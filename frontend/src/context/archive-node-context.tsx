/**
 * Archive node connection status only. Global so it survives route changes.
 * Does NOT own block feed / subscriptions — use-blockchain keeps those unchanged.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { blockchainService } from "../services/blockchain-service";

const STORAGE_KEY_URL = "ARCHIVE_NODE_URL";

export type ArchiveNodeStatus = "disconnected" | "connecting" | "connected" | "error";

interface ArchiveNodeState {
  status: ArchiveNodeStatus;
  url: string;
  lastError: string | null;
  connect: (url?: string) => Promise<void>;
  disconnect: () => Promise<void>;
}

const ArchiveNodeContext = createContext<ArchiveNodeState | null>(null);

function loadStoredUrl(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEY_URL) ?? "";
}

function saveUrl(url: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY_URL, url);
}

export function ArchiveNodeProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ArchiveNodeStatus>("disconnected");
  const [url, setUrl] = useState("");
  const [lastError, setLastError] = useState<string | null>(null);

  const connect = useCallback(async (nodeUrl?: string) => {
    const u = (nodeUrl?.trim() || loadStoredUrl() || blockchainService.getCurrentNodeUrl()) || "";
    if (!u) return;
    setStatus("connecting");
    setLastError(null);
    try {
      await blockchainService.connect(u);
      setStatus("connected");
      setUrl(u);
      saveUrl(u);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setStatus("error");
      setLastError(message);
    }
  }, []);

  const disconnect = useCallback(async () => {
    await blockchainService.disconnect();
    setStatus("disconnected");
    setLastError(null);
  }, []);

  useEffect(() => {
    const s = blockchainService.getStatus();
    const u = blockchainService.getCurrentNodeUrl();
    setStatus(s);
    if (u) setUrl(u);
    else if (loadStoredUrl()) setUrl(loadStoredUrl());
  }, []);

  const value: ArchiveNodeState = {
    status,
    url,
    lastError,
    connect,
    disconnect,
  };

  return (
    <ArchiveNodeContext.Provider value={value}>
      {children}
    </ArchiveNodeContext.Provider>
  );
}

export function useArchiveNodeStatus(): ArchiveNodeState {
  const ctx = useContext(ArchiveNodeContext);
  if (!ctx) throw new Error("useArchiveNodeStatus must be used within ArchiveNodeProvider");
  return ctx;
}
