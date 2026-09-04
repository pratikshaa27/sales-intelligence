import { api } from "@/lib/api";
import type {
  PaginatedData,
  Product,
  ProductCategory,
  ProductDocument,
  ProductFormValues,
  ProductListItem,
} from "@/types/product";
import type { ApiSuccess } from "@/types/auth";

export interface ProductListParams {
  search?: string;
  category_id?: string;
  industry?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export async function listProducts(
  params: ProductListParams,
): Promise<PaginatedData<ProductListItem>> {
  const res = await api.get<ApiSuccess<PaginatedData<ProductListItem>>>("/products", { params });
  return res.data.data;
}

export async function getProduct(id: string): Promise<Product> {
  const res = await api.get<ApiSuccess<Product>>(`/products/${id}`);
  return res.data.data;
}

export async function createProduct(values: ProductFormValues): Promise<Product> {
  const res = await api.post<ApiSuccess<Product>>("/products", values);
  return res.data.data;
}

export async function updateProduct(
  id: string,
  values: Partial<ProductFormValues>,
): Promise<Product> {
  const res = await api.patch<ApiSuccess<Product>>(`/products/${id}`, values);
  return res.data.data;
}

export async function archiveProduct(id: string): Promise<Product> {
  const res = await api.post<ApiSuccess<Product>>(`/products/${id}/archive`);
  return res.data.data;
}

export async function restoreProduct(id: string): Promise<Product> {
  const res = await api.post<ApiSuccess<Product>>(`/products/${id}/restore`);
  return res.data.data;
}

export async function deleteProduct(id: string): Promise<void> {
  await api.delete(`/products/${id}`);
}

export async function reindexProduct(id: string): Promise<Product> {
  const res = await api.post<ApiSuccess<Product>>(`/products/${id}/reindex`);
  return res.data.data;
}

export async function listProductCategories(): Promise<ProductCategory[]> {
  const res = await api.get<ApiSuccess<ProductCategory[]>>("/products/categories");
  return res.data.data;
}

export async function listProductDocuments(productId: string): Promise<ProductDocument[]> {
  const res = await api.get<ApiSuccess<ProductDocument[]>>(`/products/${productId}/documents`);
  return res.data.data;
}

export async function uploadProductDocument(
  productId: string,
  file: File,
): Promise<ProductDocument> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post<ApiSuccess<ProductDocument>>(
    `/products/${productId}/documents`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data.data;
}
