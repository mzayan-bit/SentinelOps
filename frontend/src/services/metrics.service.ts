import { axiosClient } from "@/lib/axios";
import { type PlatformMetricsResponse } from "@/types";

export const metricsService = {
  getSnapshot: async (): Promise<PlatformMetricsResponse> => {
    const { data } = await axiosClient.get<PlatformMetricsResponse>("/api/metrics");
    return data;
  },
};
