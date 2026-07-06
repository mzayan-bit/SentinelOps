import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { axiosClient } from "@/lib/axios";

interface User {
  id: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  logout: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setAccessToken = (token: string | null) => {
    setAccessTokenState(token);
    if (token) {
      localStorage.setItem("accessToken", token);
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        setUser({ id: payload.sub, email: payload.email || "", role: payload.role });
      } catch (e) {
        setUser(null);
      }
    } else {
      localStorage.removeItem("accessToken");
      setUser(null);
    }
  };

  const logout = async () => {
    try {
      await axiosClient.post("/auth/logout");
    } catch (e) {
      console.error("Logout failed", e);
    } finally {
      setAccessToken(null);
      window.location.href = "/login";
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      setAccessToken(token);
    }
    
    // Attempt silent refresh on mount
    const initAuth = async () => {
      try {
        const res = await axiosClient.post("/auth/refresh");
        setAccessToken(res.data.access_token);
      } catch (err) {
        // If refresh fails, it means no valid session
        setAccessToken(null);
      } finally {
        setIsLoading(false);
      }
    };
    
    initAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, accessToken, setAccessToken, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
