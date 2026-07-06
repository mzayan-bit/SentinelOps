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
    const token = typeof window !== 'undefined' ? localStorage.getItem("accessToken") : null;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response Interceptor
axiosClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest: any = error.config;

    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/auth/refresh') {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({resolve, reject});
        }).then(token => {
          originalRequest.headers['Authorization'] = 'Bearer ' + token;
          return axiosClient(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post<{access_token: string}>(`${env.apiUrl}/auth/refresh`, {}, { withCredentials: true });
        localStorage.setItem('accessToken', data.access_token);
        axiosClient.defaults.headers.common['Authorization'] = 'Bearer ' + data.access_token;
        processQueue(null, data.access_token);
        originalRequest.headers['Authorization'] = 'Bearer ' + data.access_token;
        return axiosClient(originalRequest);
      } catch (err) {
        processQueue(err, null);
        localStorage.removeItem('accessToken');
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response) {
      console.error(
        `[API Error] ${error.response.status} on ${error.config?.url}:`,
        error.response.data,
      );
    } else if (error.request) {
      console.error("[API Error] No response received:", error.request);
    } else {
      console.error("[API Error] Request setup failed:", error.message);
    }

    return Promise.reject(error);
  },
);
