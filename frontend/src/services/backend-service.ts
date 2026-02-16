/**
 * Backend API Service
 * 
 * Service for communicating with your custom backend API
 */

import { API_CONFIG, getApiHeaders } from "../config/api-config";

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
    return this.fetchData(API_CONFIG.backend.endpoints.partners);
  }

  /**
   * Create a new partner
   */
  async createPartner(partnerData: any) {
    return this.fetchData(API_CONFIG.backend.endpoints.partners, {
      method: "POST",
      body: JSON.stringify(partnerData),
    });
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
