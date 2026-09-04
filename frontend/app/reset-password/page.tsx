"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, extractApiErrorMessage } from "@/lib/api";
import { resetPasswordSchema, type ResetPasswordFormValues } from "@/lib/validations";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token: searchParams.get("token") ?? "" },
  });

  const onSubmit = async (values: ResetPasswordFormValues) => {
    setFormError(null);
    try {
      await api.post("/auth/reset-password", values);
      router.push("/login");
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "This reset link is invalid or has expired"));
    }
  };

  return (
    <Card className="w-full max-w-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-900">Reset password</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <Input label="Reset token" error={errors.token?.message} {...register("token")} />
        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        {formError && (
          <p role="alert" className="text-sm text-red-600">
            {formError}
          </p>
        )}
        <Button type="submit" isLoading={isSubmitting} className="w-full">
          Reset password
        </Button>
      </form>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Suspense fallback={<div className="text-slate-500">Loading…</div>}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
