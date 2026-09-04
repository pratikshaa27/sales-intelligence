"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { listProductCategories, listProducts } from "@/lib/products-api";
import { hasPermission } from "@/lib/permissions";

function ProductsPageContent() {
  const { me } = useAuth();
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data: categories } = useQuery({
    queryKey: ["product-categories"],
    queryFn: listProductCategories,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["products", { search, categoryId, status, page }],
    queryFn: () =>
      listProducts({
        search: search || undefined,
        category_id: categoryId || undefined,
        status: status || undefined,
        page,
        page_size: 20,
      }),
  });

  const canCreate = hasPermission(me?.permissions, "products.create");

  return (
    <AppShell>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Products</h1>
        {canCreate && (
          <Link href="/products/new">
            <Button>New product</Button>
          </Link>
        )}
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-4">
        <Input
          placeholder="Search by name or code"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <Select
          value={categoryId}
          onChange={(e) => {
            setPage(1);
            setCategoryId(e.target.value);
          }}
        >
          <option value="">All categories</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading products…</p>}
      {isError && <p className="text-sm text-red-600">Could not load products.</p>}
      {!isLoading && data?.items.length === 0 && (
        <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No products yet. {canCreate && "Create your first one to get started."}
        </p>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Embedding</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((product) => (
                <tr key={product.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/products/${product.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {product.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{product.code}</td>
                  <td className="px-4 py-2 text-slate-600">{product.category?.name ?? "—"}</td>
                  <td className="px-4 py-2">
                    <StatusBadge value={product.status} />
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge value={product.embedding_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.pagination.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
          <span>
            Page {data.pagination.page} of {data.pagination.total_pages} ({data.pagination.total}{" "}
            products)
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={page >= data.pagination.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function ProductsPage() {
  return (
    <ProtectedRoute>
      <ProductsPageContent />
    </ProtectedRoute>
  );
}
