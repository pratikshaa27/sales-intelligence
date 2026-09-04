"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { extractApiErrorMessage } from "@/lib/api";
import { companyFormSchema, type CompanyFormSchemaValues } from "@/lib/validations";

interface CompanyFormProps {
  defaultValues?: Partial<CompanyFormSchemaValues>;
  submitLabel: string;
  onSubmit: (values: CompanyFormSchemaValues) => Promise<void>;
}

const EMPTY_DEFAULTS: CompanyFormSchemaValues = {
  name: "",
  website: "",
  industry: "",
  locations: [],
  company_size: "",
  revenue_range: "",
  business_description: "",
  technology_stack: [],
  business_challenges: [],
  public_signals: [],
  confidence_score: 0,
};

export function CompanyForm({ defaultValues, submitLabel, onSubmit }: CompanyFormProps) {
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CompanyFormSchemaValues>({
    resolver: zodResolver(companyFormSchema),
    defaultValues: { ...EMPTY_DEFAULTS, ...defaultValues },
  });

  const submit = async (values: CompanyFormSchemaValues) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Could not save this company"));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-6" noValidate>
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Basics</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Company name" error={errors.name?.message} {...register("name")} />
          <Input
            label="Website"
            placeholder="https://example.com"
            error={errors.website?.message}
            {...register("website")}
          />
          <Input label="Industry" error={errors.industry?.message} {...register("industry")} />
          <Input
            label="Company size"
            placeholder="e.g. 51-200"
            error={errors.company_size?.message}
            {...register("company_size")}
          />
          <Input
            label="Revenue range"
            placeholder="e.g. $10M-$50M"
            error={errors.revenue_range?.message}
            {...register("revenue_range")}
          />
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
          <Textarea
            label="Business description"
            rows={4}
            error={errors.business_description?.message}
            {...register("business_description")}
          />
        </div>
      </Card>

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Research signals</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Controller
            control={control}
            name="locations"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Locations"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="technology_stack"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Technology stack"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="business_challenges"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Publicly stated business challenges"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            control={control}
            name="public_signals"
            render={({ field }) => (
              <TagInput
                name={field.name}
                label="Public signals (hiring, expansion, etc.)"
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
