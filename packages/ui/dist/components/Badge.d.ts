import * as React from "react";
export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "secondary" | "outline" | "destructive" | "success" | "warning";
}
export declare function Badge({ className, variant, ...props }: BadgeProps): React.JSX.Element;
//# sourceMappingURL=Badge.d.ts.map