import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from "../lib/utils";
export function Badge({ className, variant = "default", ...props }) {
    const dot = "before:size-1.5 before:shrink-0 before:rounded-[2px] before:content-['']";
    const variantClasses = {
        default: "border-transparent bg-muted text-foreground",
        secondary: "border-transparent bg-muted text-text-secondary",
        outline: "border-border text-foreground",
        destructive: `border-transparent bg-muted text-foreground before:bg-negative ${dot}`,
        success: `border-transparent bg-muted text-foreground before:bg-positive ${dot}`,
        warning: `border-transparent bg-muted text-foreground before:bg-warning ${dot}`
    };
    return (_jsx("div", { className: cn("inline-flex items-center gap-1.5 rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2", variantClasses[variant], className), ...props }));
}
//# sourceMappingURL=Badge.js.map