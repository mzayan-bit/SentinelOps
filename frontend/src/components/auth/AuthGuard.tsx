import React, { ReactNode } from "react";
import { useAuth } from "@/providers/auth-provider";

interface AuthGuardProps {
  children: ReactNode;
  allowedRoles?: string[];
  fallback?: ReactNode;
}

const hierarchy: Record<string, number> = {
  SUPER_ADMIN: 60,
  ORG_ADMIN: 50,
  SITE_MANAGER: 40,
  SUPERVISOR: 30,
  OPERATOR: 20,
  VIEWER: 10,
};

export function AuthGuard({ children, allowedRoles, fallback = null }: AuthGuardProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="flex items-center justify-center h-full min-h-[50vh]"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div></div>;
  }

  if (!user) {
    return <>{fallback}</>;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    // If the user's role is in the allowed list, or if their hierarchy level is greater than or equal to the minimum required role
    const minRequiredRoleLevel = Math.min(...allowedRoles.map(r => hierarchy[r] || 0));
    const userRoleLevel = hierarchy[user.role] || 0;

    if (userRoleLevel < minRequiredRoleLevel && !allowedRoles.includes(user.role)) {
       return <>{fallback}</>;
    }
  }

  return <>{children}</>;
}
