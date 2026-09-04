"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { hasPermission } from "@/lib/permissions";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", permission: null },
  { href: "/products", label: "Products", permission: "products.view" },
  { href: "/companies", label: "Companies", permission: "companies.view" },
  { href: "/contacts", label: "Contacts", permission: "contacts.view" },
  { href: "/research-jobs", label: "Research Jobs", permission: "companies.view" },
  { href: "/leads", label: "Leads", permission: "leads.view" },
  { href: "/imports", label: "Import data", permission: "leads.create" },
  { href: "/audit-logs", label: "Audit Logs", permission: "audit_logs.view" },
  { href: "/team", label: "Team", permission: "members.view" },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, logout } = useAuth();
  const router = useRouter();

  const onLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white p-4">
        <div className="mb-6 px-2 text-lg font-semibold text-brand-700">Sales Intelligence</div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.filter(
            (item) => !item.permission || hasPermission(me?.permissions, item.permission),
          ).map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="text-sm text-slate-600">
            {me?.organization_name} · <span className="font-medium">{me?.role}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-700">{me?.user.full_name}</span>
            <Button variant="secondary" onClick={onLogout}>
              Log out
            </Button>
          </div>
        </header>
        <main className="flex-1 bg-slate-50 p-6">{children}</main>
      </div>
    </div>
  );
}
