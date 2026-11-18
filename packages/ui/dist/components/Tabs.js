import { jsx as _jsx } from "react/jsx-runtime";
import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../lib/utils";
export const Tabs = TabsPrimitive.Root;
export const TabsList = React.forwardRef(({ className, ...props }, ref) => (_jsx(TabsPrimitive.List, { ref: ref, className: cn("inline-flex h-9 items-center justify-center rounded-lg bg-slate-900 p-1 text-slate-400 border border-slate-800", className), ...props })));
TabsList.displayName = TabsPrimitive.List.displayName;
export const TabsTrigger = React.forwardRef(({ className, ...props }, ref) => (_jsx(TabsPrimitive.Trigger, { ref: ref, className: cn("inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-slate-800 data-[state=active]:text-slate-100 data-[state=active]:shadow-sm cursor-pointer", className), ...props })));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;
export const TabsContent = React.forwardRef(({ className, ...props }, ref) => (_jsx(TabsPrimitive.Content, { ref: ref, className: cn("mt-2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring", className), ...props })));
TabsContent.displayName = TabsPrimitive.Content.displayName;
//# sourceMappingURL=Tabs.js.map