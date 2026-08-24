"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";
import type { UserRole } from "@/lib/api/types";

/**
 * Redirects to `redirectTo` if the user isn't authenticated, or isn't one
 * of `allowedRoles`. Returns `true` once it's safe to render the page's
 * real content (auth check finished and passed).
 *
 * Pass `skip: true` for routes that must always render regardless of auth
 * state (e.g. the login page itself, to avoid a redirect-to-self loop).
 */
export function useRequireRole(
  allowedRoles: UserRole[],
  redirectTo: string,
  skip = false
): boolean {
  const { isLoading, isAuthenticated, role } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (skip || isLoading) return;

    if (!isAuthenticated || !role || !allowedRoles.includes(role)) {
      router.replace(redirectTo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip, isLoading, isAuthenticated, role]);

  if (skip) return true;

  return !isLoading && isAuthenticated && !!role && allowedRoles.includes(role);
}