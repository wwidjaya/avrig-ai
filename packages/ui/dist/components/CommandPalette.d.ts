import * as React from "react";
export declare const Command: React.ForwardRefExoticComponent<Omit<{
    children?: React.ReactNode;
} & Pick<Pick<React.DetailedHTMLProps<React.HTMLAttributes<HTMLDivElement>, HTMLDivElement>, keyof React.HTMLAttributes<HTMLDivElement> | "key"> & {
    ref?: React.Ref<HTMLDivElement>;
} & {
    asChild?: boolean;
}, keyof React.HTMLAttributes<HTMLDivElement> | "key" | "asChild"> & {
    label?: string;
    shouldFilter?: boolean;
    filter?: (value: string, search: string, keywords?: string[]) => number;
    defaultValue?: string;
    value?: string;
    onValueChange?: (value: string) => void;
    loop?: boolean;
    disablePointerSelection?: boolean;
    vimBindings?: boolean;
} & React.RefAttributes<HTMLDivElement>, "ref"> & React.RefAttributes<HTMLDivElement>>;
export interface CommandPaletteProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    children: React.ReactNode;
}
export declare function CommandPalette({ open, onOpenChange, children }: CommandPaletteProps): React.JSX.Element;
export declare const CommandInput: React.ForwardRefExoticComponent<Omit<Omit<Pick<Pick<React.DetailedHTMLProps<React.InputHTMLAttributes<HTMLInputElement>, HTMLInputElement>, "key" | keyof React.InputHTMLAttributes<HTMLInputElement>> & {
    ref?: React.Ref<HTMLInputElement>;
} & {
    asChild?: boolean;
}, "key" | "asChild" | keyof React.InputHTMLAttributes<HTMLInputElement>>, "value" | "type" | "onChange"> & {
    value?: string;
    onValueChange?: (search: string) => void;
} & React.RefAttributes<HTMLInputElement>, "ref"> & React.RefAttributes<HTMLInputElement>>;
export declare const CommandList: React.ForwardRefExoticComponent<Omit<{
    children?: React.ReactNode;
} & Pick<Pick<React.DetailedHTMLProps<React.HTMLAttributes<HTMLDivElement>, HTMLDivElement>, keyof React.HTMLAttributes<HTMLDivElement> | "key"> & {
    ref?: React.Ref<HTMLDivElement>;
} & {
    asChild?: boolean;
}, keyof React.HTMLAttributes<HTMLDivElement> | "key" | "asChild"> & {
    label?: string;
} & React.RefAttributes<HTMLDivElement>, "ref"> & React.RefAttributes<HTMLDivElement>>;
export declare const CommandEmpty: React.ForwardRefExoticComponent<Omit<{
    children?: React.ReactNode;
} & Pick<Pick<React.DetailedHTMLProps<React.HTMLAttributes<HTMLDivElement>, HTMLDivElement>, keyof React.HTMLAttributes<HTMLDivElement> | "key"> & {
    ref?: React.Ref<HTMLDivElement>;
} & {
    asChild?: boolean;
}, keyof React.HTMLAttributes<HTMLDivElement> | "key" | "asChild"> & React.RefAttributes<HTMLDivElement>, "ref"> & React.RefAttributes<HTMLDivElement>>;
export declare const CommandGroup: React.ForwardRefExoticComponent<Omit<{
    children?: React.ReactNode;
} & Omit<Pick<Pick<React.DetailedHTMLProps<React.HTMLAttributes<HTMLDivElement>, HTMLDivElement>, keyof React.HTMLAttributes<HTMLDivElement> | "key"> & {
    ref?: React.Ref<HTMLDivElement>;
} & {
    asChild?: boolean;
}, keyof React.HTMLAttributes<HTMLDivElement> | "key" | "asChild">, "value" | "heading"> & {
    heading?: React.ReactNode;
    value?: string;
    forceMount?: boolean;
} & React.RefAttributes<HTMLDivElement>, "ref"> & React.RefAttributes<HTMLDivElement>>;
export declare const CommandItem: React.ForwardRefExoticComponent<Omit<{
    children?: React.ReactNode;
} & Omit<Pick<Pick<React.DetailedHTMLProps<React.HTMLAttributes<HTMLDivElement>, HTMLDivElement>, keyof React.HTMLAttributes<HTMLDivElement> | "key"> & {
    ref?: React.Ref<HTMLDivElement>;
} & {
    asChild?: boolean;
}, keyof React.HTMLAttributes<HTMLDivElement> | "key" | "asChild">, "value" | "disabled" | "onSelect"> & {
    disabled?: boolean;
    onSelect?: (value: string) => void;
    value?: string;
    keywords?: string[];
    forceMount?: boolean;
} & React.RefAttributes<HTMLDivElement>, "ref"> & React.RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=CommandPalette.d.ts.map