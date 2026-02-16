/**
 * Blockchain Service
 * 
 * Service for connecting to Bittensor archive node and fetching on-chain data
 */

import { ApiPromise, WsProvider } from "@polkadot/api";
import { API_CONFIG } from "../config/api-config";

class BlockchainService {
  private api: ApiPromise | null = null;
  private provider: WsProvider | null = null;
  private connectionStatus: "disconnected" | "connecting" | "connected" | "error" =
    "disconnected";
  private retryCount = 0;
  private currentNodeUrl: string = API_CONFIG.bittensor.archiveNode;

  /**
   * Connect to the Bittensor archive node with retry logic
   */
  async connect(customUrl?: string): Promise<ApiPromise> {
    if (this.api && this.connectionStatus === "connected") {
      return this.api;
    }

    const nodeUrl = customUrl || this.currentNodeUrl;
    this.currentNodeUrl = nodeUrl;

    try {
      this.connectionStatus = "connecting";
      console.log(`Attempting to connect to Bittensor node: ${nodeUrl}`);

      // Clean up existing connections
      await this.disconnect();

      // Create provider with explicit timeout
      this.provider = new WsProvider(nodeUrl, 1000, {}, 10000); // autoConnectMs, headers, timeout

      // Set up connection timeout
      const connectPromise = ApiPromise.create({
        provider: this.provider,
        throwOnConnect: true,
        throwOnUnknown: true,
        noInitWarn: true,
      });

      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Connection timeout after ${API_CONFIG.bittensor.connectionTimeout}ms`));
        }, API_CONFIG.bittensor.connectionTimeout);
      });

      this.api = await Promise.race([connectPromise, timeoutPromise]);

      // Wait for the API to be ready
      await this.api.isReady;

      this.connectionStatus = "connected";
      this.retryCount = 0;
      console.log("✓ Connected to Bittensor archive node");

      return this.api;
    } catch (error) {
      this.connectionStatus = "error";
      console.error("Failed to connect to archive node:", error);

      // Clean up failed connection immediately
      await this.disconnect();

      // Only retry the same node (don't use fallback SSL nodes)
      if (this.retryCount < 1 && !customUrl) {
        this.retryCount++;
        console.log(`Retrying connection (attempt ${this.retryCount})...`);
        
        await new Promise(resolve => setTimeout(resolve, API_CONFIG.bittensor.retryDelay));
        return this.connect(nodeUrl);
      }

      throw new Error(`Failed to connect to Bittensor node: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Disconnect from the archive node
   */
  async disconnect(): Promise<void> {
    try {
      if (this.provider) {
        await this.provider.disconnect();
      }
      if (this.api) {
        await this.api.disconnect();
      }
    } catch (error) {
      console.warn("Error during disconnect:", error);
    } finally {
      this.api = null;
      this.provider = null;
      this.connectionStatus = "disconnected";
      this.retryCount = 0;
      console.log("✓ Disconnected from archive node");
    }
  }

  /**
   * Get the current connection status
   */
  getStatus() {
    return this.connectionStatus;
  }

  /**
   * Get the current node URL
   */
  getCurrentNodeUrl() {
    return this.currentNodeUrl;
  }

  /**
   * Get the current block number
   */
  async getCurrentBlock(): Promise<number> {
    const api = await this.connect();
    const header = await api.rpc.chain.getHeader();
    return header.number.toNumber();
  }

  /**
   * Get block hash by number
   */
  async getBlockHash(blockNumber: number): Promise<string> {
    const api = await this.connect();
    const hash = await api.rpc.chain.getBlockHash(blockNumber);
    return hash.toString();
  }

  /**
   * Get block details by number
   */
  async getBlockDetails(blockNumber: number) {
    const api = await this.connect();
    const hash = await api.rpc.chain.getBlockHash(blockNumber);
    const block = await api.rpc.chain.getBlock(hash);
    const timestamp = await api.query.timestamp.now.at(hash);

    return {
      number: blockNumber,
      hash: hash.toString(),
      parentHash: block.block.header.parentHash.toString(),
      timestamp: new Date(timestamp.toNumber()).toISOString(),
      extrinsicsCount: block.block.extrinsics.length,
      extrinsics: block.block.extrinsics.map((ext, index) => ({
        index,
        hash: ext.hash.toString(),
        method: `${ext.method.section}.${ext.method.method}`,
        args: ext.method.args.toString(),
      })),
    };
  }

  /**
   * Get block range (for batch processing)
   */
  async getBlockRange(startBlock: number, endBlock: number) {
    const blocks = [];
    for (let i = startBlock; i <= endBlock; i++) {
      blocks.push(await this.getBlockDetails(i));
    }
    return blocks;
  }

  /**
   * Subscribe to new blocks (real-time updates)
   */
  async subscribeToNewBlocks(
    callback: (block: { number: number; hash: string; timestamp: string }) => void
  ) {
    const api = await this.connect();

    const unsubscribe = await api.rpc.chain.subscribeNewHeads((header) => {
      callback({
        number: header.number.toNumber(),
        hash: header.hash.toString(),
        timestamp: new Date().toISOString(),
      });
    });

    return unsubscribe;
  }

  /**
   * Get stake information for a hotkey
   */
  async getStakeForHotkey(hotkey: string, blockNumber?: number) {
    const api = await this.connect();
    
    let stakes;
    if (blockNumber) {
      const hash = await api.rpc.chain.getBlockHash(blockNumber);
      stakes = await api.query.subtensorModule.stake.at(hash, hotkey);
    } else {
      stakes = await api.query.subtensorModule.stake(hotkey);
    }

    return stakes;
  }

  /**
   * Get all delegators for a hotkey
   */
  async getDelegatorsForHotkey(hotkey: string, blockNumber?: number) {
    const api = await this.connect();
    
    let entries;
    if (blockNumber) {
      const hash = await api.rpc.chain.getBlockHash(blockNumber);
      entries = await api.query.subtensorModule.stake.entriesAt(hash);
    } else {
      entries = await api.query.subtensorModule.stake.entries();
    }

    // Filter entries for the specific hotkey
    return entries
      .filter(([key]) => key.args[0].toString() === hotkey)
      .map(([key, value]) => ({
        hotkey: key.args[0].toString(),
        delegator: key.args[1].toString(),
        stake: value.toString(),
      }));
  }
}

// Singleton instance
export const blockchainService = new BlockchainService();