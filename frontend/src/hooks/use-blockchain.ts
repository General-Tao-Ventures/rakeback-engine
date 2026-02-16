/**
 * React Hook for Blockchain Integration
 * 
 * Provides easy access to blockchain data with React state management
 */

import { useState, useEffect, useCallback } from "react";
import { blockchainService } from "../services/blockchain-service";

export function useBlockchain() {
  const [status, setStatus] = useState<"disconnected" | "connecting" | "connected" | "error">(
    "disconnected"
  );
  const [currentBlock, setCurrentBlock] = useState<number | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Connect to blockchain
  const connect = useCallback(async () => {
    try {
      setStatus("connecting");
      await blockchainService.connect();
      setStatus("connected");
      
      // Get initial block
      const block = await blockchainService.getCurrentBlock();
      setCurrentBlock(block);
    } catch (err) {
      setStatus("error");
      setError(err as Error);
      console.error("Blockchain connection error:", err);
    }
  }, []);

  // Disconnect from blockchain
  const disconnect = useCallback(async () => {
    await blockchainService.disconnect();
    setStatus("disconnected");
    setCurrentBlock(null);
  }, []);

  // Subscribe to new blocks
  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const subscribeToBlocks = async () => {
      // Only subscribe if manually connected
      if (status === "connected") {
        try {
          unsubscribe = await blockchainService.subscribeToNewBlocks((block) => {
            setCurrentBlock(block.number);
          });
        } catch (err) {
          console.error("Failed to subscribe to blocks:", err);
        }
      }
    };

    subscribeToBlocks();

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, [status]);

  return {
    status,
    currentBlock,
    error,
    connect,
    disconnect,
    // Service methods
    getCurrentBlock: () => blockchainService.getCurrentBlock(),
    getBlockDetails: (blockNumber: number) => blockchainService.getBlockDetails(blockNumber),
    getBlockRange: (start: number, end: number) => blockchainService.getBlockRange(start, end),
    getStakeForHotkey: (hotkey: string, blockNumber?: number) =>
      blockchainService.getStakeForHotkey(hotkey, blockNumber),
    getDelegatorsForHotkey: (hotkey: string, blockNumber?: number) =>
      blockchainService.getDelegatorsForHotkey(hotkey, blockNumber),
  };
}