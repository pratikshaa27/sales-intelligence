"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "@/lib/validations";

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = async (values: ForgotPasswordFormValues) => {
    await api.post("/auth/forgot-password", values);
    // Always show the same message, whether or not the email exists, so the response
    // never reveals account existence.
    setSubmitted(true);
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <h1 className="mb-6 text-2xl font-semibold text-slate-900">Forgot password</h1>
        {submitted ? (
          <p className="text-sm text-slate-700">
            If an account with that email exists, a reset link has been sent.
          </p>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <Button type="submit" isLoading={isSubmitting} className="w-full">
              Send reset link
            </Button>
          </form>
        )}
        <div className="mt-4 text-sm text-slate-600">
          <Link href="/login" className="text-brand-600 hover:underline">
            Back to sign in
          </Link>
        </div>
      </Card>
    </main>
  );
}
