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
import { loginSchema, type LoginFormValues } from "@/lib/validations";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginFormValues) => {
    setFormError(null);
    try {
      await login(values.email, values.password);
      router.push("/dashboard");
    } catch (error) {
      setFormError(extractApiErrorMessage(error, "Invalid email or password"));
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <h1 className="mb-6 text-2xl font-semibold text-slate-900">Sign in</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register("email")}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            error={errors.password?.message}
            {...register("password")}
          />
          {formError && (
            <p role="alert" className="text-sm text-red-600">
              {formError}
            </p>
          )}
          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Sign in
          </Button>
        </form>
        <div className="mt-4 flex justify-between text-sm text-slate-600">
          <Link href="/forgot-password" className="hover:text-brand-600">
            Forgot password?
          </Link>
          <Link href="/register" className="hover:text-brand-600">
            Register an organization
          </Link>
        </div>
      </Card>
    </main>
  );
}
