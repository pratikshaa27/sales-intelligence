"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/hooks/use-auth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { me, isBootstrapping, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isBootstrapping && !isLoading && !me) {
      router.replace("/login");
    }
  }, [isBootstrapping, isLoading, me, router]);

  if (isBootstrapping || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Loading…
      </div>
    );
  }

  if (!me) {
    return null;
  }

  return <>{children}</>;
}
