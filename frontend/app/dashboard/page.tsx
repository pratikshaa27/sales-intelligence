"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { useAuth } from "@/hooks/use-auth";
import {
  getDashboard,
  getLeadsAnalytics,
  getProductsAnalytics,
  getTeamAnalytics,
} from "@/lib/analytics-api";
import { hasPermission } from "@/lib/permissions";

const CHART_COLORS = [
  "#4f46e5",
  "#0ea5e9",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
];

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
    </Card>
  );
}

function ChartCard({
  title,
  description,
  children,
  table,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  table: React.ReactNode;
}) {
  return (
    <Card>
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      {description && <p className="mb-2 text-xs text-slate-500">{description}</p>}
      <div className="mt-3 h-64 w-full">{children}</div>
      <div className="mt-4 overflow-x-auto">
        <p className="mb-1 text-xs font-medium text-slate-500">Data table</p>
        {table}
      </div>
    </Card>
  );
}

function DashboardPageContent() {
  const { me } = useAuth();
  const canViewOrg =
    hasPermission(me?.permissions, "analytics.view_org") || Boolean(me?.user.is_superadmin);

  const dashboardQuery = useQuery({ queryKey: ["analytics", "dashboard"], queryFn: getDashboard });
  const leadsAnalyticsQuery = useQuery({
    queryKey: ["analytics", "leads"],
    queryFn: getLeadsAnalytics,
  });
  const productsAnalyticsQuery = useQuery({
    queryKey: ["analytics", "products"],
    queryFn: getProductsAnalytics,
    enabled: canViewOrg,
  });
  const teamAnalyticsQuery = useQuery({
    queryKey: ["analytics", "team"],
    queryFn: getTeamAnalytics,
    enabled: canViewOrg,
  });

  const dashboard = dashboardQuery.data;
  const leadsAnalytics = leadsAnalyticsQuery.data;
  const productsAnalytics = productsAnalyticsQuery.data;
  const teamAnalytics = teamAnalyticsQuery.data;

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">
          Welcome back, {me?.user.full_name}
        </h1>
        <p className="text-sm text-slate-500">
          {dashboard?.scope === "organization"
            ? "Showing performance across the whole organization."
            : "Showing your assigned leads and activity."}
        </p>
      </div>

      {dashboardQuery.isLoading && <p className="text-sm text-slate-500">Loading dashboard…</p>}
      {dashboardQuery.isError && (
        <p className="text-sm text-red-600">Could not load dashboard data.</p>
      )}

      {dashboard && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total leads" value={dashboard.total_leads} />
            <StatCard label="High-priority leads" value={dashboard.high_priority_leads} />
            <StatCard label="Average lead score" value={`${dashboard.average_lead_score}/100`} />
            <StatCard
              label="Companies researched"
              value={dashboard.total_companies_researched}
            />
            <StatCard label="New leads" value={dashboard.new_leads} />
            <StatCard label="Assigned leads" value={dashboard.assigned_leads} />
            <StatCard label="Contacted leads" value={dashboard.contacted_leads} />
            <StatCard label="Won / Lost" value={`${dashboard.won_leads} / ${dashboard.lost_leads}`} />
            <StatCard label="Research jobs running" value={dashboard.research_jobs_running} />
            <StatCard label="Research jobs completed" value={dashboard.research_jobs_completed} />
            {leadsAnalytics && (
              <StatCard label="Win rate" value={`${leadsAnalytics.win_rate}%`} />
            )}
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard title="Leads by status" table={
              <table className="w-full text-left text-sm">
                <thead className="text-slate-500">
                  <tr>
                    <th className="py-1 pr-4">Status</th>
                    <th className="py-1">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.leads_by_status.map((item) => (
                    <tr key={item.status} className="border-t border-slate-100">
                      <td className="py-1 pr-4 capitalize text-slate-700">
                        {item.status.replace(/_/g, " ")}
                      </td>
                      <td className="py-1 text-slate-600">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }>
              {dashboard.leads_by_status.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dashboard.leads_by_status}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="status"
                      tickFormatter={(v: string) => v.replace(/_/g, " ")}
                      tick={{ fontSize: 11 }}
                      interval={0}
                      angle={-30}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-500">No leads yet.</p>
              )}
            </ChartCard>

            <ChartCard title="Leads by product" table={
              <table className="w-full text-left text-sm">
                <thead className="text-slate-500">
                  <tr>
                    <th className="py-1 pr-4">Product</th>
                    <th className="py-1">Leads</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.leads_by_product.map((item) => (
                    <tr key={item.product_id} className="border-t border-slate-100">
                      <td className="py-1 pr-4 text-slate-700">{item.product_name}</td>
                      <td className="py-1 text-slate-600">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }>
              {dashboard.leads_by_product.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={dashboard.leads_by_product}
                      dataKey="count"
                      nameKey="product_name"
                      outerRadius={80}
                      label={(entry) => entry.product_name}
                    >
                      {dashboard.leads_by_product.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-500">No leads yet.</p>
              )}
            </ChartCard>

            <ChartCard title="Leads by industry" table={
              <table className="w-full text-left text-sm">
                <thead className="text-slate-500">
                  <tr>
                    <th className="py-1 pr-4">Industry</th>
                    <th className="py-1">Leads</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.leads_by_industry.map((item) => (
                    <tr key={item.industry} className="border-t border-slate-100">
                      <td className="py-1 pr-4 text-slate-700">{item.industry}</td>
                      <td className="py-1 text-slate-600">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }>
              {dashboard.leads_by_industry.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dashboard.leads_by_industry} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis dataKey="industry" type="category" width={100} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-500">No leads yet.</p>
              )}
            </ChartCard>

            <Card>
              <h2 className="mb-3 text-lg font-semibold text-slate-900">Recent activity</h2>
              {dashboard.recent_activities.length > 0 ? (
                <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto text-sm">
                  {dashboard.recent_activities.map((activity, i) => (
                    <li key={i} className="border-b border-slate-100 pb-2 last:border-0">
                      <span className="font-medium text-slate-800">{activity.lead_name}</span>{" "}
                      <span className="text-slate-600">{activity.description}</span>
                      <p className="text-xs text-slate-400">
                        {new Date(activity.created_at).toLocaleString()}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">No activity recorded yet.</p>
              )}
            </Card>
          </div>

          {canViewOrg && (dashboard.team_performance.length > 0 || teamAnalytics) && (
            <Card className="mt-6">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">Team performance</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 text-slate-500">
                    <tr>
                      <th className="py-2 pr-4">Team member</th>
                      <th className="py-2 pr-4">Assigned</th>
                      <th className="py-2 pr-4">Won</th>
                      <th className="py-2 pr-4">Lost</th>
                      <th className="py-2 pr-4">Win rate</th>
                      <th className="py-2">Average score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(teamAnalytics?.team ?? dashboard.team_performance).map((member) => (
                      <tr key={member.user_id} className="border-b border-slate-100 last:border-0">
                        <td className="py-2 pr-4 text-slate-800">{member.full_name}</td>
                        <td className="py-2 pr-4 text-slate-600">{member.assigned_count}</td>
                        <td className="py-2 pr-4 text-slate-600">{member.won_count}</td>
                        <td className="py-2 pr-4 text-slate-600">{member.lost_count}</td>
                        <td className="py-2 pr-4 text-slate-600">{member.win_rate}%</td>
                        <td className="py-2 text-slate-600">{member.average_score}/100</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {canViewOrg && productsAnalytics && (
            <Card className="mt-6">
              <h2 className="mb-3 text-lg font-semibold text-slate-900">Product performance</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-200 text-slate-500">
                    <tr>
                      <th className="py-2 pr-4">Product</th>
                      <th className="py-2 pr-4">Leads generated</th>
                      <th className="py-2 pr-4">Average score</th>
                      <th className="py-2 pr-4">Won</th>
                      <th className="py-2">Win rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {productsAnalytics.products.map((product) => (
                      <tr
                        key={product.product_id}
                        className="border-b border-slate-100 last:border-0"
                      >
                        <td className="py-2 pr-4 text-slate-800">{product.product_name}</td>
                        <td className="py-2 pr-4 text-slate-600">{product.lead_count}</td>
                        <td className="py-2 pr-4 text-slate-600">{product.average_score}/100</td>
                        <td className="py-2 pr-4 text-slate-600">{product.won_count}</td>
                        <td className="py-2 text-slate-600">{product.win_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardPageContent />
    </ProtectedRoute>
  );
}
