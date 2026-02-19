/**
 * TaoStats API Service
 *
 * Service for fetching data from TaoStats API.
 * TaoStats requires the token in the Authorization header (not x-api-key).
 */

import { API_CONFIG, getTaoStatsApiKey } from "../config/api-config";

/** Build TaoStats request headers in one place. Key from localStorage/env via getTaoStatsApiKey(). */
function getTaoStatsRequestHeaders(overrideKey?: string): Record<string, string> {
  const key = (overrideKey ?? getTaoStatsApiKey())?.trim() || "";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (key) {
    // TaoStats expects the raw token in Authorization (no Bearer prefix)
    headers["Authorization"] = key;
  }
  return headers;
}

let authHeaderLogged = false;
function logAuthHeaderOnce(present: boolean) {
  if (import.meta.env?.DEV && !authHeaderLogged) {
    authHeaderLogged = true;
    console.log("TaoStats request auth: Authorization header present =", present);
  }
}

class TaoStatsService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.taoStats.baseUrl;
  }

  /**
   * Generic fetch method. Uses centralized headers with Authorization: Bearer <key>.
   */
  private async fetchData<T>(endpoint: string, overrideKey?: string): Promise<T> {
    const headers = getTaoStatsRequestHeaders(overrideKey);
    logAuthHeaderOnce(!!headers["Authorization"]);

    try {
      const url = `${this.baseUrl}${endpoint}`;
      console.log("TaoStats API Request:", url);

      const response = await fetch(url, { headers });

      console.log("TaoStats API Response:", response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("TaoStats API Error Response:", errorText);
        throw new Error(`TaoStats API error (${response.status}): ${response.statusText || errorText}`);
      }

      const data = await response.json();
      console.log("TaoStats API Data:", data);
      return data;
    } catch (error) {
      console.error("TaoStats fetch error:", error);
      throw error;
    }
  }

  /**
   * Test connection with optional key (e.g. from settings before save).
   * Returns { ok, status, statusCode }. Use for Test Connection button.
   */
  async testConnection(overrideKey?: string): Promise<{ ok: boolean; status: number; message?: string }> {
    const key = (overrideKey ?? getTaoStatsApiKey())?.trim();
    const url = `${this.baseUrl}${API_CONFIG.taoStats.endpoints.network}`;
    const headers = getTaoStatsRequestHeaders(key ?? undefined);
    logAuthHeaderOnce(!!headers["Authorization"]);

    const response = await fetch(url, { headers });
    const text = await response.text();
    let message: string | undefined;
    if (!response.ok) {
      try {
        const json = JSON.parse(text);
        message = json?.message ?? text;
      } catch {
        message = text || response.statusText;
      }
    }
    return {
      ok: response.ok,
      status: response.status,
      message: message || undefined,
    };
  }

  /**
   * Get network statistics
   */
  async getNetworkStats() {
    return this.fetchData(API_CONFIG.taoStats.endpoints.network);
  }

  /**
   * Get all validators
   */
  async getValidators() {
    return this.fetchData(API_CONFIG.taoStats.endpoints.validators);
  }

  /**
   * Get validator by hotkey
   */
  async getValidatorByHotkey(hotkey: string) {
    return this.fetchData(`${API_CONFIG.taoStats.endpoints.validators}/${hotkey}`);
  }

  /**
   * Get all delegators
   */
  async getDelegators() {
    return this.fetchData(API_CONFIG.taoStats.endpoints.delegators);
  }

  /**
   * Get delegator by address
   */
  async getDelegatorByAddress(address: string) {
    return this.fetchData(`${API_CONFIG.taoStats.endpoints.delegators}/${address}`);
  }

  /**
   * Get subnet information
   */
  async getSubnets() {
    return this.fetchData(API_CONFIG.taoStats.endpoints.subnets);
  }

  /**
   * Get subnet by ID
   */
  async getSubnetById(subnetId: number) {
    return this.fetchData(`${API_CONFIG.taoStats.endpoints.subnets}/${subnetId}`);
  }

  /**
   * Get emissions data
   */
  async getEmissions(params?: { from?: string; to?: string; subnet?: number }) {
    let url = API_CONFIG.taoStats.endpoints.emissions;
    
    if (params) {
      const queryParams = new URLSearchParams();
      if (params.from) queryParams.append("from", params.from);
      if (params.to) queryParams.append("to", params.to);
      if (params.subnet) queryParams.append("subnet", params.subnet.toString());
      
      if (queryParams.toString()) {
        url += `?${queryParams.toString()}`;
      }
    }

    return this.fetchData(url);
  }

  /**
   * Get TAO price data (v1 API requires ?asset=tao)
   */
  async getPrice() {
    return this.fetchData(`${API_CONFIG.taoStats.endpoints.price}?asset=tao`);
  }
}

// Singleton instance
export const taoStatsService = new TaoStatsService();