import { axiosClient } from "@/lib/axios";
import { type ReportMetadata, type ReportRequest } from "@/types";

export const reportService = {
  getReports: async (): Promise<ReportMetadata[]> => {
    const { data } = await axiosClient.get<ReportMetadata[]>("/api/reports");
    return data;
  },

  generateReport: async (payload: ReportRequest): Promise<{ task_id: string; status: string }> => {
    const { data } = await axiosClient.post<{ task_id: string; status: string }>(
      "/api/reports/generate",
      payload,
    );
    return data;
  },

  // Note: For downloads, we typically just use <a href="..."> on the frontend to leverage browser native saving.
  // But we can expose this for edge cases where we want to process the blob.
  downloadReportBlob: async (id: string): Promise<Blob> => {
    const { data } = await axiosClient.get<Blob>(`/api/reports/${id}/download`, {
      responseType: "blob",
    });
    return data;
  },
};
