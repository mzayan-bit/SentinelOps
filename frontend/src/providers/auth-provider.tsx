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
  const [accessToken, setAccessTokenState] = useState<string | null>("mock-token");
  const [user, setUser] = useState<User | null>({
    id: "admin",
    email: "admin@sentinelops.ai",
    role: "SUPER_ADMIN"
  });
  const [isLoading, setIsLoading] = useState(false);

  const setAccessToken = (token: string | null) => {
    // Disabled logic for bypassing auth
  };

  const logout = async () => {
    // Disabled for bypassing auth
  };

  useEffect(() => {
    // Disabled effect for bypassing auth
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
