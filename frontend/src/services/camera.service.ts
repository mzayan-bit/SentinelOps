import { axiosClient } from "@/lib/axios";
import { type Camera } from "@/types";

export const cameraService = {
  getCameras: async (): Promise<Camera[]> => {
    const { data } = await axiosClient.get<Camera[]>("/api/cameras");
    return data;
  },

  getCamera: async (id: string): Promise<Camera> => {
    const { data } = await axiosClient.get<Camera>(`/api/cameras/${id}`);
    return data;
  },
};
