import { forwardRef, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, id, children, ...props }, ref) => {
    const inputId = id ?? props.name;
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-slate-700">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={inputId}
          className={cn(
            "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900",
            "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100",
            error && "border-red-400 focus:border-red-500 focus:ring-red-100",
            className,
          )}
          aria-invalid={Boolean(error)}
          {...props}
        >
          {children}
        </select>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  },
);
Select.displayName = "Select";
