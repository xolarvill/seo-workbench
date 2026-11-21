import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/** shadcn Badge with the workbench status tone variants. */
const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden whitespace-nowrap rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold leading-[1.2] tracking-normal capitalize [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        neutral: "border-separator bg-canvas text-ink-muted",
        success: "border-[#a7f3d0] bg-success-wash text-success-dark",
        warning: "border-[#fde68a] bg-warning-wash text-warning-dark",
        danger: "border-[#fecaca] bg-danger-wash text-danger-dark",
        info: "border-[#bfdbfe] bg-info-wash text-info-dark",
        secondary: "border-transparent bg-surface-soft text-ink-muted",
        outline: "border-separator-strong text-ink-muted",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot : "span";
  return <Comp data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
