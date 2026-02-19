/**
 * Backend API Service
 *
 * Service for communicating with your custom backend API
 */

import { API_CONFIG, getApiHeaders } from "../config/api-config";

/** Partner as returned by API */
export interface Partner {
  id: string;
  name: string;
  type: "Named" | "Tag-based" | "Hybrid";
  rakebackRate: number;
  priority: number;
  status: string;
  createdBy: string;
  createdDate: string;
  walletAddress?: string;
  memoTag?: string;
  applyFromDate?: string;
  payoutAddress?: string;
  rules?: EligibilityRule[];
}

/** Payload for creating a partner */
export interface PartnerCreate {
  name: string;
  type: "named" | "tag-based" | "hybrid";
  rakebackRate: number;
  priority: number;
  payoutAddress?: string;
  walletAddress?: string;
  walletLabel?: string;
  memoKeyword?: string;
  matchType?: string;
  applyFromDate?: string;
  applyFromBlock?: number;
  hybridWallet?: string;
  hybridWalletLabel?: string;
  hybridMemo?: string;
  hybridMatchType?: string;
}

/** Payload for updating a partner */
export interface PartnerUpdate {
  name?: string;
  rakebackRate?: number;
  priority?: number;
  payoutAddress?: string;
  partnerType?: string;
}

/** Eligibility rule */
export interface EligibilityRule {
  id: string;
  partnerId: string;
  type: "wallet" | "memo" | "subnet-filter";
  config: Record<string, unknown>;
  appliesFromBlock: number;
  createdAt: string;
  createdBy: string;
}

/** Payload for adding a rule */
export interface RuleCreate {
  type: "wallet" | "memo" | "subnet-filter";
  config: Record<string, unknown>;
  appliesFromBlock?: number;
}

/** Rule change audit log entry */
export interface RuleChangeLogEntry {
  timestamp: string;
  user: string;
  action: string;
  partner: string;
  details: string;
  appliesFromBlock: number;
}

/** Attribution record returned by API */
export interface Attribution {
  id: string;
  blockNumber: number;
  validatorHotkey: string;
  delegatorAddress: string;
  delegationType: string;
  subnetId: number | null;
  attributedDtao: string;
  delegationProportion: string;
  completenessFlag: string;
  taoAllocated: string;
  fullyAllocated: boolean;
}

/** Attribution stats summary */
export interface AttributionStats {
  totalBlocks: number;
  blocksWithAttributions: number;
  totalAttributions: number;
  totalDtaoAttributed: string;
  uniqueDelegators: number;
}

/** Block detail with all delegator attributions */
export interface BlockDetail {
  blockNumber: number;
  timestamp: string | null;
  validatorHotkey: string;
  totalDtao: string;
  delegatorCount: number;
  completenessFlag: string;
  attributions: Attribution[];
}

/** Conversion event returned by API */
export interface ConversionEvent {
  id: string;
  blockNumber: number;
  transactionHash: string;
  validatorHotkey: string;
  dtaoAmount: string;
  taoAmount: string;
  conversionRate: string;
  subnetId: number | null;
  fullyAllocated: boolean;
  taoPrice: number | null;
}

/** Allocation detail for a conversion */
export interface AllocationDetail {
  id: string;
  conversionEventId: string;
  blockAttributionId: string;
  taoAllocated: string;
  allocationMethod: string;
  completenessFlag: string;
}

/** Conversion detail with allocations */
export interface ConversionDetail {
  conversion: ConversionEvent;
  allocations: AllocationDetail[];
}

/** Ingestion trigger result */
export interface IngestionResult {
  runId: string;
  blocksProcessed: number;
  blocksCreated: number;
  blocksSkipped: number;
  attributionsCreated: number;
  errors: string[];
}

/** Conversion ingestion result */
export interface ConversionIngestionResult {
  runId: string;
  blocksProcessed: number;
  eventsCreated: number;
  eventsSkipped: number;
  errors: string[];
}

class BackendService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.backend.baseUrl;
  }

  /**
   * Generic fetch method
   */
  private async fetchData<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          ...getApiHeaders(),
          ...options?.headers,
        },
      });

      if (!response.ok) {
        let detail = response.statusText;
        try {
          const errBody = await response.json();
          if (errBody?.detail) detail = errBody.detail;
          if (errBody?.type) detail = `[${errBody.type}] ${detail}`;
        } catch {
          // ignore JSON parse failure
        }
        throw new Error(`Backend API error: ${detail}`);
      }

      return await response.json();
    } catch (error) {
      console.error("Backend fetch error:", error);
      throw error;
    }
  }

  /**
   * Get all partners
   */
  async getPartners() {
    return this.fetchData<Partner[]>(API_CONFIG.backend.endpoints.partners);
  }

  /**
   * Get a single partner with rules
   */
  async getPartner(partnerId: string) {
    return this.fetchData<Partner>(`${API_CONFIG.backend.endpoints.partners}/${partnerId}`);
  }

  /**
   * Create a new partner
   */
  async createPartner(partnerData: PartnerCreate) {
    return this.fetchData<Partner>(API_CONFIG.backend.endpoints.partners, {
      method: "POST",
      body: JSON.stringify(partnerData),
    });
  }

  /**
   * Update a partner
   */
  async updatePartner(partnerId: string, updates: Partial<PartnerUpdate>) {
    return this.fetchData<Partner>(`${API_CONFIG.backend.endpoints.partners}/${partnerId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    });
  }

  /**
   * Get rule change audit log
   */
  async getRuleChangeLog(limit = 100) {
    return this.fetchData<RuleChangeLogEntry[]>(
      `${API_CONFIG.backend.endpoints.partners}/rule-change-log/list?limit=${limit}`
    );
  }

  /**
   * Add a rule to a partner
   */
  async addPartnerRule(partnerId: string, rule: RuleCreate) {
    return this.fetchData<EligibilityRule>(
      `${API_CONFIG.backend.endpoints.partners}/${partnerId}/rules`,
      {
        method: "POST",
        body: JSON.stringify(rule),
      }
    );
  }

  async getAttributions(
    startBlock: number,
    endBlock: number,
    params?: { validator_hotkey?: string; subnet_id?: number }
  ) {
    const qp = new URLSearchParams({
      start: String(startBlock),
      end: String(endBlock),
    });
    if (params?.validator_hotkey) qp.append("validator_hotkey", params.validator_hotkey);
    if (params?.subnet_id != null) qp.append("subnet_id", String(params.subnet_id));
    return this.fetchData<Attribution[]>(
      `${API_CONFIG.backend.endpoints.attributions}?${qp.toString()}`
    );
  }

  async getAttributionStats(startBlock: number, endBlock: number, validatorHotkey?: string) {
    const qp = new URLSearchParams({
      start: String(startBlock),
      end: String(endBlock),
    });
    if (validatorHotkey) qp.append("validator_hotkey", validatorHotkey);
    return this.fetchData<AttributionStats>(
      `${API_CONFIG.backend.endpoints.attributions}/stats?${qp.toString()}`
    );
  }

  async getBlockDetail(blockNumber: number, validatorHotkey?: string) {
    const qp = new URLSearchParams();
    if (validatorHotkey) qp.append("validator_hotkey", validatorHotkey);
    const qs = qp.toString() ? `?${qp.toString()}` : "";
    return this.fetchData<BlockDetail>(
      `${API_CONFIG.backend.endpoints.attributions}/block/${blockNumber}${qs}`
    );
  }

  async getConversions(params?: { startBlock?: number; endBlock?: number }) {
    const qp = new URLSearchParams();
    if (params?.startBlock != null) qp.append("start_block", String(params.startBlock));
    if (params?.endBlock != null) qp.append("end_block", String(params.endBlock));
    const qs = qp.toString() ? `?${qp.toString()}` : "";
    return this.fetchData<ConversionEvent[]>(
      `${API_CONFIG.backend.endpoints.conversions}${qs}`
    );
  }

  async getConversionDetail(conversionId: string) {
    return this.fetchData<ConversionDetail>(
      `${API_CONFIG.backend.endpoints.conversions}/${conversionId}`
    );
  }

  async triggerIngestion(startBlock: number, endBlock: number, validatorHotkey: string) {
    const qp = new URLSearchParams({
      start_block: String(startBlock),
      end_block: String(endBlock),
      validator_hotkey: validatorHotkey,
    });
    return this.fetchData<IngestionResult>(
      `${API_CONFIG.backend.endpoints.attributions}/ingest?${qp.toString()}`,
      { method: "POST" }
    );
  }

  async triggerConversionIngestion(startBlock: number, endBlock: number, validatorHotkey?: string) {
    const qp = new URLSearchParams({
      start_block: String(startBlock),
      end_block: String(endBlock),
    });
    if (validatorHotkey) qp.append("validator_hotkey", validatorHotkey);
    return this.fetchData<ConversionIngestionResult>(
      `${API_CONFIG.backend.endpoints.conversions}/ingest?${qp.toString()}`,
      { method: "POST" }
    );
  }

  /**
   * Get rakeback ledger
   */
  async getRakebackLedger(partnerId?: string) {
    let url = API_CONFIG.backend.endpoints.rakeback;

    if (partnerId) {
      url += `?partnerId=${partnerId}`;
    }

    return this.fetchData(url);
  }

  /**
   * Export rakeback data
   */
  async exportRakeback(params: {
    partnerId?: string;
    from?: string;
    to?: string;
    format?: "csv" | "json";
  }) {
    const queryParams = new URLSearchParams();
    if (params.partnerId) queryParams.append("partnerId", params.partnerId);
    if (params.from) queryParams.append("from", params.from);
    if (params.to) queryParams.append("to", params.to);
    if (params.format) queryParams.append("format", params.format);

    const url = `${API_CONFIG.backend.endpoints.exports}?${queryParams.toString()}`;

    return this.fetchData(url);
  }
}

// Singleton instance
export const backendService = new BackendService();
