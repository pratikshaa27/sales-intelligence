"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { extractApiErrorMessage } from "@/lib/api";
import { listCompanies } from "@/lib/companies-api";
import { listContacts } from "@/lib/contacts-api";
import { listProducts } from "@/lib/products-api";
import { createLeadFormSchema, type CreateLeadFormValues } from "@/lib/validations";

interface LeadFormProps {
  defaultValues?: Partial<CreateLeadFormValues>;
  lockCompany?: boolean;
  submitLabel: string;
  onSubmit: (values: CreateLeadFormValues) => Promise<void>;
}

const EMPTY_DEFAULTS: CreateLeadFormValues = {
  company_id: "",
  product_id: "",
  contact_id: "",
  name: "",
  source: "manual",
  tags: [],
};

export function LeadForm({ defaultValues, lockCompany, submitLabel, onSubmit }: LeadFormProps) {
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateLeadFormValues>({
    resolver: zodResolver(createLeadFormSchema),
    defaultValues: { ...EMPTY_DEFAULTS, ...defaultValues },
  });

  const companyId = watch("company_id");

  const { data: companiesPage } = useQuery({
    queryKey: ["companies", "for-select"],
    queryFn: () => listCompanies({ page: 1, page_size: 100 }),
  });
  const { data: productsPage } = useQuery({
    queryKey: ["products", "for-select"],
    queryFn: () => listProducts({ page: 1, page_size: 100 }),
  });
  const { data: contactsPage } = useQuery({
    queryKey: ["contacts", { company_id: companyId }],
    queryFn: () => listContacts({ company_id: companyId, page: 1, page_size: 100 }),
    enabled: Boolean(companyId),
  });

  const submit = async (values: CreateLeadFormValues) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not save this lead"));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-6" noValidate>
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Lead details</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Controller
            control={control}
            name="company_id"
            render={({ field }) => (
              <Select
                name={field.name}
                label="Company"
                error={errors.company_id?.message}
                value={field.value}
                onChange={field.onChange}
                disabled={lockCompany}
              >
                <option value="">Select a company…</option>
                {companiesPage?.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            )}
          />
          <Controller
            control={control}
            name="product_id"
            render={({ field }) => (
              <Select
                name={field.name}
                label="Product"
                error={errors.product_id?.message}
                value={field.value}
                onChange={field.onChange}
              >
                <option value="">Select a product…</option>
                {productsPage?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            )}
          />
          <Controller
            control={control}
            name="contact_id"
            render={({ field }) => (
              <Select
                name={field.name}
                label="Decision-maker contact (optional)"
                value={field.value}
                onChange={field.onChange}
                disabled={!companyId}
              >
                <option value="">No contact linked yet</option>
                {contactsPage?.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} — {c.job_title}
                  </option>
                ))}
              </Select>
            )}
          />
          <Input label="Lead name" error={errors.name?.message} {...register("name")} />
          <Input label="Source" error={errors.source?.message} {...register("source")} />
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
