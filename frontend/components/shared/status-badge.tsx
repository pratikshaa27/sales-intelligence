import { cn } from "@/lib/utils";

const COLOR_MAP: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  active: "bg-green-100 text-green-700",
  archived: "bg-amber-100 text-amber-700",
  none: "bg-slate-100 text-slate-500",
  queued: "bg-blue-100 text-blue-700",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  new: "bg-slate-100 text-slate-700",
  researching: "bg-blue-100 text-blue-700",
  qualified: "bg-indigo-100 text-indigo-700",
  assigned: "bg-indigo-100 text-indigo-700",
  contacted: "bg-blue-100 text-blue-700",
  meeting_scheduled: "bg-purple-100 text-purple-700",
  proposal_sent: "bg-purple-100 text-purple-700",
  negotiation: "bg-amber-100 text-amber-700",
  won: "bg-green-100 text-green-700",
  lost: "bg-red-100 text-red-700",
  disqualified: "bg-red-100 text-red-700",
  low: "bg-slate-100 text-slate-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-amber-100 text-amber-700",
  critical: "bg-red-100 text-red-700",
};

export function StatusBadge({ value }: { value: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        COLOR_MAP[value] ?? "bg-slate-100 text-slate-700",
      )}
    >
      {value}
    </span>
  );
}
