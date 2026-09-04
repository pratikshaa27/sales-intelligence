"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { extractApiErrorMessage } from "@/lib/api";
import { registerSchema, type RegisterFormValues } from "@/lib/validations";

export default function RegisterPage() {
  const { register: registerOrganization } = useAuth();
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values: RegisterFormValues) => {
    setFormError(null);
    try {
      await registerOrganization(values);
      router.push("/dashboard");
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Registration failed"));
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md">
        <h1 className="mb-1 text-2xl font-semibold text-slate-900">Register your organization</h1>
        <p className="mb-6 text-sm text-slate-600">
          Creates your organization and its first admin account.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <Input
            label="Organization name"
            error={errors.organization_name?.message}
            {...register("organization_name")}
          />
          <Input
            label="Your full name"
            error={errors.admin_full_name?.message}
            {...register("admin_full_name")}
          />
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.admin_email?.message}
            {...register("admin_email")}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            error={errors.admin_password?.message}
            {...register("admin_password")}
          />
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Create organization
          </Button>
        </form>
        <div className="mt-4 text-sm text-slate-600">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-600 hover:underline">
            Sign in
          </Link>
        </div>
      </Card>
    </main>
  );
}
