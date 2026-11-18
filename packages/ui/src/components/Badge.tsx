import * as React from "react";
import { cn } from "../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "destructive" | "success" | "warning";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "border-transparent bg-blue-600 text-white hover:bg-blue-700",
    secondary: "border-transparent bg-slate-800 text-slate-100 hover:bg-slate-700",
    outline: "text-slate-300 border-slate-700",
    destructive: "border-transparent bg-red-600 text-white hover:bg-red-700",
    success: "border-transparent bg-emerald-600 text-white hover:bg-emerald-700",
    warning: "border-transparent bg-amber-600 text-white hover:bg-amber-700"
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
