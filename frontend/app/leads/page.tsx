"use client";

import { ProtectedRoute } from "@/components/shared/protected-route";
import { LeadsPageContent } from "@/app/leads/leads-page-content";

export default function LeadsPage() {
  return (
    <ProtectedRoute>
      <LeadsPageContent />
    </ProtectedRoute>
  );
}
