"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { ProductForm } from "@/components/forms/product-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { getProduct, updateProduct } from "@/lib/products-api";
import type { ProductFormSchemaValues } from "@/lib/validations";

function EditProductContent() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const productId = params.id;

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getProduct(productId),
  });

  const onSubmit = async (values: ProductFormSchemaValues) => {
    await updateProduct(productId, values);
    router.push(`/products/${productId}`);
  };

  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Edit product</h1>
      {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {product && (
        <ProductForm
          defaultValues={{ ...product, category_id: product.category?.id ?? null }}
          submitLabel="Save changes"
          onSubmit={onSubmit}
        />
      )}
    </AppShell>
  );
}

export default function EditProductPage() {
  return (
    <ProtectedRoute>
      <EditProductContent />
    </ProtectedRoute>
  );
}
