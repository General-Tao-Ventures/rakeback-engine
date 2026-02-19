/**
 * React Hook for Blockchain Integration
 *
 * Status/connect/disconnect come from global archive-node context so they persist across navigation.
 * Block feed (currentBlock + subscription) stays in this hook — unchanged.
 */

import { useState, useEffect } from "react";
import { useArchiveNodeStatus } from "../context/archive-node-context";
import { blockchainService } from "../services/blockchain-service";

export function useBlockchain() {
  const archive = useArchiveNodeStatus();
  const [currentBlock, setCurrentBlock] = useState<number | null>(null);

  // Block feed: subscribe when connected. No cleanup that disconnects the socket.
  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const subscribeToBlocks = async () => {
      if (archive.status === "connected") {
        try {
          const block = await blockchainService.getCurrentBlock();
          setCurrentBlock(block);
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
  }, [archive.status]);

  return {
    status: archive.status,
    currentBlock,
    error: archive.lastError ? new Error(archive.lastError) : null,
    connect: archive.connect,
    disconnect: archive.disconnect,
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