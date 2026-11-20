import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import * as React from "react";
import { Command as CommandPrimitive } from "cmdk";
import { Search } from "lucide-react";
import { cn } from "../lib/utils";
import { Dialog, DialogContent } from "./Dialog";
export const Command = React.forwardRef(({ className, ...props }, ref) => (_jsx(CommandPrimitive, { ref: ref, className: cn("flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground", className), ...props })));
Command.displayName = CommandPrimitive.displayName;
export function CommandPalette({ open, onOpenChange, children }) {
    return (_jsx(Dialog, { open: open, onOpenChange: onOpenChange, children: _jsx(DialogContent, { className: "overflow-hidden p-0 shadow-lg", children: _jsx(Command, { className: "[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5", children: children }) }) }));
}
export const CommandInput = React.forwardRef(({ className, ...props }, ref) => (_jsxs("div", { className: "flex items-center border-b border-border px-3", "cmdk-input-wrapper": "", children: [_jsx(Search, { className: "mr-2 h-4 w-4 shrink-0 opacity-50" }), _jsx(CommandPrimitive.Input, { ref: ref, className: cn("flex h-11 w-full rounded-md bg-transparent py-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset disabled:cursor-not-allowed disabled:opacity-50", className), ...props })] })));
CommandInput.displayName = CommandPrimitive.Input.displayName;
export const CommandList = React.forwardRef(({ className, ...props }, ref) => (_jsx(CommandPrimitive.List, { ref: ref, className: cn("max-h-[300px] overflow-y-auto overflow-x-hidden p-1", className), ...props })));
CommandList.displayName = CommandPrimitive.List.displayName;
export const CommandEmpty = React.forwardRef((props, ref) => (_jsx(CommandPrimitive.Empty, { ref: ref, className: "py-6 text-center text-sm text-muted-foreground", ...props })));
CommandEmpty.displayName = CommandPrimitive.Empty.displayName;
export const CommandGroup = React.forwardRef(({ className, ...props }, ref) => (_jsx(CommandPrimitive.Group, { ref: ref, className: cn("overflow-hidden p-1 text-popover-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground", className), ...props })));
CommandGroup.displayName = CommandPrimitive.Group.displayName;
export const CommandItem = React.forwardRef(({ className, ...props }, ref) => (_jsx(CommandPrimitive.Item, { ref: ref, className: cn("relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-muted aria-selected:text-foreground data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50", className), ...props })));
CommandItem.displayName = CommandPrimitive.Item.displayName;
//# sourceMappingURL=CommandPalette.js.map