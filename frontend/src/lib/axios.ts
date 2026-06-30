import axios, { AxiosError } from "axios";
import { env } from "./env";

export const axiosClient = axios.create({
  baseURL: env.apiUrl,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor
axiosClient.interceptors.request.use(
  (config) => {
    // You can attach auth tokens here if needed
    // const token = localStorage.getItem('token');
    // if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response Interceptor
axiosClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    // Centralized error handling
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error(
        `[API Error] ${error.response.status} on ${error.config?.url}:`,
        error.response.data,
      );

      if (error.response.status === 401) {
        // Handle unauthorized (e.g., redirect to login)
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error("[API Error] No response received:", error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error("[API Error] Request setup failed:", error.message);
    }

    return Promise.reject(error);
  },
);
