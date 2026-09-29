import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/* Primary actions are ink on paper; hover runs a highlighter over them. Text on
   the highlighter stays dark in both themes, because yellow never carries
   light text. */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded font-semibold tracking-[-0.005em] transition-[background-color,border-color,color,box-shadow] duration-200 disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "bg-ink text-ground hover:bg-marker hover:text-[hsl(30_12%_10%)]",
        accent: "bg-accent text-accent-ink hover:bg-accent/90",
        outline: "border border-ink/80 bg-transparent text-ink hover:bg-marker hover:border-marker hover:text-[hsl(30_12%_10%)]",
        ghost: "text-ink-soft hover:bg-surface-sunken hover:text-ink",
        alert: "bg-alert text-accent-ink hover:bg-alert/90",
        link: "text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent",
      },
      size: {
        default: "h-10 px-4 text-sm",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />
  )
);
Button.displayName = "Button";

export { Button, buttonVariants };
