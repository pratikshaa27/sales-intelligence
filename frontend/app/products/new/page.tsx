"use client";

import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { ProductForm } from "@/components/forms/product-form";
import { ProtectedRoute } from "@/components/shared/protected-route";
import { createProduct } from "@/lib/products-api";
import type { ProductFormSchemaValues } from "@/lib/validations";

function NewProductContent() {
  const router = useRouter();

  const onSubmit = async (values: ProductFormSchemaValues) => {
    const product = await createProduct(values);
    router.push(`/products/${product.id}`);
  };

  return (
    <AppShell>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">New product</h1>
      <ProductForm submitLabel="Create product" onSubmit={onSubmit} />
    </AppShell>
  );
}

export default function NewProductPage() {
  return (
    <ProtectedRoute>
      <NewProductContent />
    </ProtectedRoute>
  );
}
