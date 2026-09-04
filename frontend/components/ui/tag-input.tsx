"use client";

import { X } from "lucide-react";
import { useState, type KeyboardEvent } from "react";

import { cn } from "@/lib/utils";

export interface TagInputProps {
  id?: string;
  name?: string;
  label?: string;
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function TagInput({
  id,
  name,
  label,
  value,
  onChange,
  placeholder,
  className,
}: TagInputProps) {
  const [draft, setDraft] = useState("");
  const inputId = id ?? name;

  const commitDraft = () => {
    const trimmed = draft.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
    setDraft("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commitDraft();
    } else if (e.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-300 px-2 py-1.5 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-sm text-brand-700"
          >
            {tag}
            <button
              type="button"
              onClick={() => onChange(value.filter((t) => t !== tag))}
              aria-label={`Remove ${tag}`}
              className="rounded-full hover:bg-brand-100"
            >
              <X size={12} />
            </button>
          </span>
        ))}
        <input
          id={inputId}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commitDraft}
          placeholder={value.length === 0 ? placeholder : ""}
          className="min-w-[120px] flex-1 border-none py-0.5 text-sm outline-none"
        />
      </div>
    </div>
  );
}
