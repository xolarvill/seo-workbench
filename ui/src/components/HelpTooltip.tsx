import { CircleHelp } from "lucide-react";
import type { ReactNode } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const alignment = { left: "start", center: "center", right: "end" } as const;

/**
 * Shared help bubble. Radix Tooltip provides the hover/focus wiring, dismiss
 * behavior, and collision-aware placement; the classes keep the workbench
 * bubble shape (lead-in strong + supporting list).
 */
export function HelpTooltip({ label, children, align = "left" }: { label: string; children: ReactNode; align?: "left" | "center" | "right" }) {
  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <span
          role="img"
          tabIndex={0}
          aria-label={`Help: ${label}`}
          className={cn(
            "helpTooltip inline-flex size-6 shrink-0 cursor-help items-center justify-center rounded-full text-muted-foreground",
            align === "right" && "helpTooltipRight",
            align === "center" && "helpTooltipCenter",
          )}
        >
          <CircleHelp aria-hidden="true" size={14} strokeWidth={1.8} />
        </span>
      </TooltipTrigger>
      <TooltipContent
        side="bottom"
        align={alignment[align]}
        sideOffset={7}
        className="w-max max-w-[min(320px,calc(100vw-32px))] px-3 py-[11px] text-left text-[12px]/[1.5] font-normal tracking-normal normal-case whitespace-normal [&>li]:m-0 [&>li]:pl-0.5 [&>li]:text-ink-muted [&>strong]:mb-[7px] [&>strong]:block [&>strong]:font-bold [&>strong]:text-ink [&>ul]:m-0 [&>ul]:grid [&>ul]:gap-[5px] [&>ul]:pl-4"
      >
        {children}
      </TooltipContent>
    </Tooltip>
  );
}
