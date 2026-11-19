"use client";
import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog";
import { cn } from "../lib/utils";
import { Button } from "./Button";
function AlertDialog({ ...props }) {
    return _jsx(AlertDialogPrimitive.Root, { "data-slot": "alert-dialog", ...props });
}
function AlertDialogTrigger({ ...props }) {
    return _jsx(AlertDialogPrimitive.Trigger, { "data-slot": "alert-dialog-trigger", ...props });
}
function AlertDialogPortal({ ...props }) {
    return _jsx(AlertDialogPrimitive.Portal, { "data-slot": "alert-dialog-portal", ...props });
}
function AlertDialogOverlay({ className, ...props }) {
    return (_jsx(AlertDialogPrimitive.Overlay, { "data-slot": "alert-dialog-overlay", className: cn(
        // overflow-hidden turns the backdrop into a non-scrollable scroll container,
        // which is required for overscroll-contain to take effect.
        "fixed inset-0 z-50 overflow-hidden overscroll-contain bg-black/50 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0", className), ...props }));
}
function AlertDialogContent({ className, size = "default", ...props }) {
    return (_jsxs(AlertDialogPortal, { children: [_jsx(AlertDialogOverlay, {}), _jsx(AlertDialogPrimitive.Content, { "data-slot": "alert-dialog-content", "data-size": size, className: cn("group/alert-dialog-content fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 overscroll-contain rounded-lg border bg-background p-6 shadow-lg duration-200 data-[size=sm]:max-w-xs data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[size=default]:sm:max-w-lg", className), ...props })] }));
}
function AlertDialogHeader({ className, ...props }) {
    return (_jsx("div", { "data-slot": "alert-dialog-header", className: cn("grid grid-rows-[auto_1fr] place-items-center gap-1.5 text-center has-data-[slot=alert-dialog-media]:grid-rows-[auto_auto_1fr] has-data-[slot=alert-dialog-media]:gap-x-6 sm:group-data-[size=default]/alert-dialog-content:place-items-start sm:group-data-[size=default]/alert-dialog-content:text-left sm:group-data-[size=default]/alert-dialog-content:has-data-[slot=alert-dialog-media]:grid-rows-[auto_1fr]", className), ...props }));
}
function AlertDialogFooter({ className, ...props }) {
    return (_jsx("div", { "data-slot": "alert-dialog-footer", className: cn("flex flex-col-reverse gap-2 group-data-[size=sm]/alert-dialog-content:grid group-data-[size=sm]/alert-dialog-content:grid-cols-2 sm:flex-row sm:justify-end", className), ...props }));
}
function AlertDialogTitle({ className, ...props }) {
    return (_jsx(AlertDialogPrimitive.Title, { "data-slot": "alert-dialog-title", className: cn("text-lg font-semibold sm:group-data-[size=default]/alert-dialog-content:group-has-data-[slot=alert-dialog-media]/alert-dialog-content:col-start-2", className), ...props }));
}
function AlertDialogDescription({ className, ...props }) {
    return (_jsx(AlertDialogPrimitive.Description, { "data-slot": "alert-dialog-description", className: cn("text-sm text-muted-foreground", className), ...props }));
}
function AlertDialogMedia({ className, ...props }) {
    return (_jsx("div", { "data-slot": "alert-dialog-media", className: cn("mb-2 inline-flex size-16 items-center justify-center rounded-md bg-muted sm:group-data-[size=default]/alert-dialog-content:row-span-2 *:[svg:not([class*='size-'])]:size-8", className), ...props }));
}
function AlertDialogAction({ className, variant = "default", size = "default", children, ...props }) {
    // The shared Button has no asChild support, so the slot direction is inverted:
    // Radix Action renders asChild into Button instead of Button into Action.
    // Because the Button is the slot target, the caller's children must land on the
    // Button itself. Children written as JSX here would override the ones arriving
    // through prop spreading, which is what silently dropped the button labels, so
    // `children` is destructured out of `props` and passed to the Button explicitly.
    return (_jsx(AlertDialogPrimitive.Action, { asChild: true, ...props, children: _jsx(Button, { "data-slot": "alert-dialog-action", variant: variant, size: size, className: className, children: children }) }));
}
function AlertDialogCancel({ className, variant = "outline", size = "default", children, ...props }) {
    return (_jsx(AlertDialogPrimitive.Cancel, { asChild: true, ...props, children: _jsx(Button, { "data-slot": "alert-dialog-cancel", variant: variant, size: size, className: className, children: children }) }));
}
export { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogMedia, AlertDialogOverlay, AlertDialogPortal, AlertDialogTitle, AlertDialogTrigger };
//# sourceMappingURL=AlertDialog.js.map