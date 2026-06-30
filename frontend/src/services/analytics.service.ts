import { axiosClient } from "@/lib/axios";
import { type AnalyticsSummaryResponse, type RecommendationResponse } from "@/types";

export const analyticsService = {
  getSummary: async (): Promise<AnalyticsSummaryResponse> => {
    const { data } = await axiosClient.get<AnalyticsSummaryResponse>("/api/analytics/summary");
    return data;
  },

  getRecommendations: async (): Promise<RecommendationResponse> => {
    const { data } = await axiosClient.get<RecommendationResponse>(
      "/api/analytics/recommendations",
    );
    return data;
  },
};
