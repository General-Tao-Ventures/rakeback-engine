import { useState, useEffect } from "react";
import { taoStatsService } from "../services/taostats-service";

interface TaoPriceData {
  price: number;
  price24hAgo: number;
  change24h: number;
  changePercent24h: number;
  isLoading: boolean;
  error: string | null;
}

/**
 * Hook to fetch TAO price data from TaoStats API
 */
export function useTaoPrice(refreshInterval: number = 60000): TaoPriceData {
  const [priceData, setPriceData] = useState<TaoPriceData>({
    price: 0,
    price24hAgo: 0,
    change24h: 0,
    changePercent24h: 0,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;

    const fetchPrice = async () => {
      try {
        // TaoStats v1 returns { data: [ {...} ], pagination }
        let raw: any;
        try {
          raw = await taoStatsService.getPrice();
        } catch (priceError) {
          console.log("Price endpoint failed, trying network stats:", priceError);
          raw = await taoStatsService.getNetworkStats();
        }

        if (!isMounted) return;

        const data = raw?.data?.[0] ?? raw;
        const currentPrice = Number(
          data?.price ??
            data?.current_price ??
            data?.tao_price ??
            data?.marketPrice ??
            data?.price_usd ??
            0
        );
        const percentChange24h = data?.percent_change_24h != null
          ? Number(data.percent_change_24h)
          : null;
        const previous24h =
          percentChange24h != null && currentPrice > 0
            ? currentPrice / (1 + percentChange24h / 100)
            : currentPrice;
        const change = currentPrice - previous24h;
        const changePercent =
          percentChange24h != null ? percentChange24h : (previous24h > 0 ? (change / previous24h) * 100 : 0);

        setPriceData({
          price: currentPrice,
          price24hAgo: previous24h,
          change24h: change,
          changePercent24h: changePercent,
          isLoading: false,
          error: currentPrice === 0 ? "Price data not available from API" : null,
        });
      } catch (error) {
        if (!isMounted) return;
        
        console.error("Failed to fetch TAO price:", error);
        
        // Use fallback mock data if API fails
        const fallbackPrice = 487.32;
        const fallbackPrevious = 471.85;
        
        setPriceData({
          price: fallbackPrice,
          price24hAgo: fallbackPrevious,
          change24h: fallbackPrice - fallbackPrevious,
          changePercent24h: ((fallbackPrice - fallbackPrevious) / fallbackPrevious) * 100,
          isLoading: false,
          error: "Using fallback data - API unavailable",
        });
      }
    };

    fetchPrice();
    const interval = setInterval(fetchPrice, refreshInterval);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [refreshInterval]);

  return priceData;
}