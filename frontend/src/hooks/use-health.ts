import useSWR from "swr";
import { axiosClient } from "@/lib/axios";

export interface HealthResponse {
  status: string;
  version?: string;
}

const fetcher = (url: string) => axiosClient.get<HealthResponse>(url).then((res) => res.data);

export function useHealth(pollIntervalMs = 15000) {
  const { data, error, isLoading } = useSWR<HealthResponse>("/health", fetcher, {
    refreshInterval: pollIntervalMs,
    revalidateOnFocus: true,
  });

  const isOnline = data?.status === "ok";
  
  return {
    isOnline,
    isError: !!error,
    isLoading,
    status: isOnline ? "online" : error ? "error" : "loading",
  };
}
