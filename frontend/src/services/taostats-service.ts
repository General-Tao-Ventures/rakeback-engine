/**
 * TaoStats API Service
 * 
 * Service for fetching data from TaoStats API
 */

import { API_CONFIG, getApiHeaders } from "../config/api-config";

class TaoStatsService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.taoStats.baseUrl;
  }

  /**
   * Generic fetch method (uses getApiHeaders which reads key from localStorage or env)
   */
  private async fetchData<T>(endpoint: string): Promise<T> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      console.log('TaoStats API Request:', url);

      const response = await fetch(url, {
        headers: getApiHeaders(),
      });

      console.log('TaoStats API Response:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('TaoStats API Error Response:', errorText);
        throw new Error(`TaoStats API error (${response.status}): ${response.statusText || errorText}`);
      }

      const data = await response.json();
      console.log('TaoStats API Data:', data);
      return data;
    } catch (error) {
      console.error("TaoStats fetch error:", error);
      throw error;
    }
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