"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";
import type { UserRole } from "@/lib/api/types";

/**
 * Redirects to `redirectTo` if the user isn't authenticated, or isn't one
 * of `allowedRoles`. Returns `true` once it's safe to render the page's
 * real content (auth check finished and passed).
 */
export function useRequireRole(allowedRoles: UserRole[], redirectTo: string): boolean {
  const { isLoading, isAuthenticated, role } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated || !role || !allowedRoles.includes(role)) {
      router.replace(redirectTo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, isAuthenticated, role]);

  return !isLoading && isAuthenticated && !!role && allowedRoles.includes(role);
}
