import { axiosClient } from "@/lib/axios";
import { type Alert } from "@/types";

export const alertService = {
  getAlerts: async (): Promise<Alert[]> => {
    const { data } = await axiosClient.get<Alert[]>("/api/alerts");
    return data;
  },

  getAlert: async (id: string): Promise<Alert> => {
    const { data } = await axiosClient.get<Alert>(`/api/alerts/${id}`);
    return data;
  },
};
