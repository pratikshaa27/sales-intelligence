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
import { contactFormSchema, type ContactFormSchemaValues } from "@/lib/validations";

interface ContactFormProps {
  defaultValues?: Partial<ContactFormSchemaValues>;
  lockCompany?: boolean;
  submitLabel: string;
  onSubmit: (values: ContactFormSchemaValues) => Promise<void>;
}

const EMPTY_DEFAULTS: ContactFormSchemaValues = {
  company_id: "",
  full_name: "",
  job_title: "",
  department: "",
  seniority: "",
  role_relevance: "",
  profile_url: "",
  business_email: "",
  business_phone: "",
  confidence_score: 0,
};

export function ContactForm({
  defaultValues,
  lockCompany,
  submitLabel,
  onSubmit,
}: ContactFormProps) {
  const [formError, setFormError] = useState<string | null>(null);
  const { data: companiesPage } = useQuery({
    queryKey: ["companies", "for-select"],
    queryFn: () => listCompanies({ page: 1, page_size: 100 }),
  });

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ContactFormSchemaValues>({
    resolver: zodResolver(contactFormSchema),
    defaultValues: { ...EMPTY_DEFAULTS, ...defaultValues },
  });

  const submit = async (values: ContactFormSchemaValues) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not save this contact"));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-6" noValidate>
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Contact details</h2>
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
          <Input label="Full name" error={errors.full_name?.message} {...register("full_name")} />
          <Input label="Job title" error={errors.job_title?.message} {...register("job_title")} />
          <Input
            label="Department"
            error={errors.department?.message}
            {...register("department")}
          />
          <Input label="Seniority" placeholder="e.g. VP" {...register("seniority")} />
          <Input
            label="Confidence score (0-100)"
            type="number"
            min={0}
            max={100}
            error={errors.confidence_score?.message}
            {...register("confidence_score", { valueAsNumber: true })}
          />
        </div>
        <div className="mt-4">
          <Input
            label="Role relevance"
            placeholder="Why this role matters for buying decisions"
            error={errors.role_relevance?.message}
            {...register("role_relevance")}
          />
        </div>
      </Card>

      <Card>
        <h2 className="mb-1 text-lg font-semibold text-slate-900">
          Public professional contact info
        </h2>
        <p className="mb-4 text-sm text-slate-500">
          Only public, professionally-sourced business contact details belong here — never personal
          email, personal phone, or other private information.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label="Public profile URL"
            placeholder="https://www.linkedin.com/in/..."
            {...register("profile_url")}
          />
          <Input label="Business email" {...register("business_email")} />
          <Input label="Business phone" {...register("business_phone")} />
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
