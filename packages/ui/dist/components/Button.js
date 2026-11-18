import { jsx as _jsx } from "react/jsx-runtime";
import * as React from "react";
import { cn } from "../lib/utils";
export const Button = React.forwardRef(({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseClasses = "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 cursor-pointer";
    const variantClasses = {
        default: "bg-blue-600 text-white shadow hover:bg-blue-700 active:bg-blue-800",
        secondary: "bg-slate-800 text-slate-100 shadow-sm hover:bg-slate-700 active:bg-slate-900",
        outline: "border border-slate-700 bg-transparent shadow-sm hover:bg-slate-800 hover:text-slate-100",
        ghost: "hover:bg-slate-800 hover:text-slate-100",
        destructive: "bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800"
    };
    const sizeClasses = {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9"
    };
    return (_jsx("button", { ref: ref, className: cn(baseClasses, variantClasses[variant], sizeClasses[size], className), ...props }));
});
Button.displayName = "Button";
//# sourceMappingURL=Button.js.map