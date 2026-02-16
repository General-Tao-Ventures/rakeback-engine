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
        throw new Error(`Backend API error: ${response.statusText}`);
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

  /**
   * Get attributions for a block range
   */
  async getAttributions(startBlock: number, endBlock: number) {
    return this.fetchData(
      `${API_CONFIG.backend.endpoints.attributions}?start=${startBlock}&end=${endBlock}`
    );
  }

  /**
   * Get conversion events
   */
  async getConversions(params?: { from?: string; to?: string }) {
    let url = API_CONFIG.backend.endpoints.conversions;

    if (params) {
      const queryParams = new URLSearchParams();
      if (params.from) queryParams.append("from", params.from);
      if (params.to) queryParams.append("to", params.to);

      if (queryParams.toString()) {
        url += `?${queryParams.toString()}`;
      }
    }

    return this.fetchData(url);
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
