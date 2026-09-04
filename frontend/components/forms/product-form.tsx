"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { extractApiErrorMessage } from "@/lib/api";
import { listProductCategories } from "@/lib/products-api";
import { productFormSchema, type ProductFormSchemaValues } from "@/lib/validations";

interface ProductFormProps {
  defaultValues?: Partial<ProductFormSchemaValues>;
  submitLabel: string;
  onSubmit: (values: ProductFormSchemaValues) => Promise<void>;
}

const EMPTY_DEFAULTS: ProductFormSchemaValues = {
  name: "",
  code: "",
  category_id: null,
  short_description: "",
  detailed_description: "",
  target_industries: [],
  target_company_size: [],
  target_geographic_regions: [],
  business_problems: [],
  key_features: [],
  benefits: [],
  pricing_model: "",
  minimum_contract_value: null,
  required_technical_capabilities: [],
  supported_integrations: [],
  ideal_customer_profile: "",
  common_use_cases: [],
  competitor_alternatives: [],
};

export function ProductForm({ defaultValues, submitLabel, onSubmit }: ProductFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const { data: categories } = useQuery({
    queryKey: ["product-categories"],
    queryFn: listProductCategories,
  });

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormSchemaValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: { ...EMPTY_DEFAULTS, ...defaultValues },
  });

  const submit = async (values: ProductFormSchemaValues) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not save this product"));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-6" noValidate>
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Basics</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Product name" error={errors.name?.message} {...register("name")} />
          <Input label="Product code" error={errors.code?.message} {...register("code")} />
          <Controller
            control={control}
            name="category_id"
            render={({ field }) => (
              <Select
                name={field.name}
                label="Category"
                value={field.value ?? ""}
                onChange={(e) => field.onChange(e.target.value || null)}
              >
                <option value="">Uncategorized</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            )}
          />
          <Input
            label="Pricing model"
            placeholder="e.g. Per-seat subscription"
            error={errors.pricing_model?.message}
            {...register("pricing_model")}
          />
          <Input
            label="Minimum contract value ($)"
            type="number"
            step="0.01"
            error={errors.minimum_contract_value?.message}
            {...register("minimum_contract_value", {
              setValueAs: (v) => (v === "" ? null : Number(v)),
            })}
          />
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4">
          <Textarea
            label="Short description"
            rows={2}
            error={errors.short_description?.message}
            {...register("short_description")}
          />
          <Textarea
            label="Detailed description"
            rows={5}
            error={errors.detailed_description?.message}
            {...register("detailed_description")}
          />
          <Textarea
            label="Ideal customer profile"
            rows={3}
            error={errors.ideal_customer_profile?.message}
            {...register("ideal_customer_profile")}
          />
        </div>
      </Card>

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Targeting</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Controller
            control={control}
            name="target_industries"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Target industries"
                value={field.value}
                onChange={field.onChange}
                placeholder="Add an industry and press Enter"
              />
            )}
          />
          <Controller
            control={control}
            name="target_company_size"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Target company size"
                value={field.value}
                onChange={field.onChange}
                placeholder="e.g. 51-200"
              />
            )}
          />
          <Controller
            control={control}
            name="target_geographic_regions"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Target geographic regions"
                value={field.value}
                onChange={field.onChange}
                placeholder="e.g. North America"
              />
            )}
          />
          <Controller
            control={control}
            name="business_problems"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Business problems solved"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </div>
      </Card>

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Capabilities</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Controller
            control={control}
            name="key_features"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Key features"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="benefits"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Benefits"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="required_technical_capabilities"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Required technical capabilities"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="supported_integrations"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Supported integrations"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="common_use_cases"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Common use cases"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="competitor_alternatives"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Competitor alternatives"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </div>
      </Card>

      {formError && (
        <p role="alert" className="text-sm text-red-600">
          {formError}
        </p>
      )}
      <Button type="submit" isLoading={isSubmitting} className="self-start">
        {submitLabel}
      </Button>
    </form>
  );
}
