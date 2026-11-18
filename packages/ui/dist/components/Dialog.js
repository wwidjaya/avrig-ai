import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import * as React from "react";
import { cn } from "../lib/utils";
export function Dialog({ open, onOpenChange, children }) {
    if (!open)
        return null;
    return (_jsxs("div", { className: "fixed inset-0 z-50 flex items-center justify-center", children: [_jsx("div", { className: "fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity", onClick: () => onOpenChange(false) }), _jsx("div", { className: "relative z-50 w-full max-w-lg scale-100 p-4 transition-all", children: children })] }));
}
export const DialogContent = React.forwardRef(({ className, children, ...props }, ref) => (_jsx("div", { ref: ref, className: cn("w-full rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl text-slate-100", className), ...props, children: children })));
DialogContent.displayName = "DialogContent";
export const DialogHeader = ({ className, ...props }) => (_jsx("div", { className: cn("flex flex-col space-y-1.5 text-center sm:text-left", className), ...props }));
DialogHeader.displayName = "DialogHeader";
export const DialogFooter = ({ className, ...props }) => (_jsx("div", { className: cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", className), ...props }));
DialogFooter.displayName = "DialogFooter";
export const DialogTitle = React.forwardRef(({ className, ...props }, ref) => (_jsx("h2", { ref: ref, className: cn("text-lg font-semibold leading-none tracking-tight text-slate-100", className), ...props })));
DialogTitle.displayName = "DialogTitle";
export const DialogDescription = React.forwardRef(({ className, ...props }, ref) => (_jsx("p", { ref: ref, className: cn("text-sm text-slate-400", className), ...props })));
DialogDescription.displayName = "DialogDescription";
//# sourceMappingURL=Dialog.js.map