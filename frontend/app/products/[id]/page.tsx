"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { extractApiErrorMessage } from "@/lib/api";
import { hasPermission } from "@/lib/permissions";
import {
  archiveProduct,
  deleteProduct,
  getProduct,
  listProductDocuments,
  reindexProduct,
  restoreProduct,
  uploadProductDocument,
} from "@/lib/products-api";

function TagList({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span key={v} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function ProductDetailContent() {
  const { me } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const productId = params.id;
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const productQuery = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getProduct(productId),
    refetchInterval: (query) =>
      query.state.data?.embedding_status === "queued" ||
      query.state.data?.embedding_status === "processing"
        ? 1500
        : false,
  });
  const documentsQuery = useQuery({
    queryKey: ["product-documents", productId],
    queryFn: () => listProductDocuments(productId),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["product", productId] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
  };

  const runAction = async (action: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await action();
      invalidate();
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Action failed"));
    }
  };

  const onFileSelected = async (file: File | undefined) => {
    if (!file) return;
    setActionError(null);
    try {
      await uploadProductDocument(productId, file);
      queryClient.invalidateQueries({ queryKey: ["product-documents", productId] });
    } catch (error) {
      setActionError(extractApiErrorMessage(error, "Upload failed"));
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const product = productQuery.data;
  const canEdit = hasPermission(me?.permissions, "products.edit");
  const canArchive = hasPermission(me?.permissions, "products.archive");
  const canDelete = hasPermission(me?.permissions, "products.delete");

  if (productQuery.isLoading) {
    return (
      <AppShell>
        <p className="text-sm text-slate-500">Loading product…</p>
      </AppShell>
    );
  }

  if (!product) {
    return (
      <AppShell>
        <p className="text-sm text-red-600">Product not found.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-slate-900">{product.name}</h1>
            <StatusBadge value={product.status} />
          </div>
          <p className="text-sm text-slate-500">
            {product.code} · {product.category?.name ?? "Uncategorized"}
          </p>
        </div>
        <div className="flex gap-2">
          {canEdit && (
            <Link href={`/products/${productId}/edit`}>
              <Button variant="secondary">Edit</Button>
            </Link>
          )}
          {canArchive && product.status !== "archived" && (
            <Button variant="secondary" onClick={() => runAction(() => archiveProduct(productId))}>
              Archive
            </Button>
          )}
          {canArchive && product.status === "archived" && (
            <Button variant="secondary" onClick={() => runAction(() => restoreProduct(productId))}>
              Restore
            </Button>
          )}
          {canDelete && product.status === "draft" && (
            <Button
              variant="destructive"
              onClick={() =>
                runAction(async () => {
                  await deleteProduct(productId);
                  router.push("/products");
                })
              }
            >
              Delete
            </Button>
          )}
        </div>
      </div>

      {actionError && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {actionError}
        </p>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Overview</h2>
            <p className="text-sm text-slate-700">{product.short_description}</p>
            {product.detailed_description && (
              <p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">
                {product.detailed_description}
              </p>
            )}
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Pricing model</dt>
                <dd className="text-slate-800">{product.pricing_model || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Minimum contract value</dt>
                <dd className="text-slate-800">
                  {product.minimum_contract_value != null
                    ? `$${product.minimum_contract_value.toLocaleString()}`
                    : "—"}
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Targeting & capabilities</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TagList label="Target industries" values={product.target_industries} />
              <TagList label="Target company size" values={product.target_company_size} />
              <TagList
                label="Target geographic regions"
                values={product.target_geographic_regions}
              />
              <TagList label="Business problems solved" values={product.business_problems} />
              <TagList label="Key features" values={product.key_features} />
              <TagList label="Benefits" values={product.benefits} />
              <TagList
                label="Required technical capabilities"
                values={product.required_technical_capabilities}
              />
              <TagList label="Supported integrations" values={product.supported_integrations} />
              <TagList label="Common use cases" values={product.common_use_cases} />
              <TagList label="Competitor alternatives" values={product.competitor_alternatives} />
            </div>
            {product.ideal_customer_profile && (
              <div className="mt-4">
                <p className="text-sm font-medium text-slate-500">Ideal customer profile</p>
                <p className="mt-1 text-sm text-slate-700">{product.ideal_customer_profile}</p>
              </div>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">AI matching</h2>
              <StatusBadge value={product.embedding_status} />
            </div>
            <p className="mb-3 text-sm text-slate-500">
              Embeddings let the research engine match this product against prospective
              companies. Regenerate them after changing the description, features, or ICP.
            </p>
            {canEdit && (
              <Button
                variant="secondary"
                onClick={() => runAction(() => reindexProduct(productId))}
                disabled={product.embedding_status === "queued" || product.embedding_status === "processing"}
              >
                Regenerate embeddings
              </Button>
            )}
          </Card>

          <Card>
            <h2 className="mb-2 text-lg font-semibold text-slate-900">Documents</h2>
            {canEdit && (
              <div className="mb-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.doc,.docx,.txt,.md"
                  onChange={(e) => onFileSelected(e.target.files?.[0])}
                  className="text-sm"
                />
              </div>
            )}
            {documentsQuery.data?.length ? (
              <ul className="flex flex-col gap-2">
                {documentsQuery.data.map((doc) => (
                  <li key={doc.id} className="flex justify-between text-sm text-slate-700">
                    <span className="truncate">{doc.file_name}</span>
                    <span className="text-slate-400">{Math.round(doc.size_bytes / 1024)} KB</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No documents uploaded yet.</p>
            )}
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

export default function ProductDetailPage() {
  return (
    <ProtectedRoute>
      <ProductDetailContent />
    </ProtectedRoute>
  );
}
