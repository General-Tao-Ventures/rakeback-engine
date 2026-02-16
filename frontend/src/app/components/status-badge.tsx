import { cn } from "./ui/utils";

export type StatusType =
  | "complete"
  | "partial"
  | "missing"
  | "pending"
  | "approved"
  | "paid"
  | "active"
  | "disabled"
  | "allocated"
  | "unallocated";

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
}

const statusConfig: Record<
  StatusType,
  { label: string; color: string; bg: string }
> = {
  complete: {
    label: "Complete",
    color: "text-emerald-400",
    bg: "bg-emerald-950/50 border-emerald-900/50",
  },
  partial: {
    label: "Partial",
    color: "text-amber-400",
    bg: "bg-amber-950/50 border-amber-900/50",
  },
  missing: {
    label: "Missing Data",
    color: "text-red-400",
    bg: "bg-red-950/50 border-red-900/50",
  },
  pending: {
    label: "Pending",
    color: "text-zinc-400",
    bg: "bg-zinc-900/50 border-zinc-800",
  },
  approved: {
    label: "Approved",
    color: "text-blue-400",
    bg: "bg-blue-950/50 border-blue-900/50",
  },
  paid: {
    label: "Paid",
    color: "text-emerald-400",
    bg: "bg-emerald-950/50 border-emerald-900/50",
  },
  active: {
    label: "Active",
    color: "text-emerald-400",
    bg: "bg-emerald-950/50 border-emerald-900/50",
  },
  disabled: {
    label: "Disabled",
    color: "text-zinc-500",
    bg: "bg-zinc-900/50 border-zinc-800",
  },
  allocated: {
    label: "Allocated",
    color: "text-emerald-400",
    bg: "bg-emerald-950/50 border-emerald-900/50",
  },
  unallocated: {
    label: "Unallocated",
    color: "text-amber-400",
    bg: "bg-amber-950/50 border-amber-900/50",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium border rounded",
        config.color,
        config.bg,
        className
      )}
    >
      <div className={cn("h-1.5 w-1.5 rounded-full", config.color.replace('text-', 'bg-'))} />
      {config.label}
    </span>
  );
}
