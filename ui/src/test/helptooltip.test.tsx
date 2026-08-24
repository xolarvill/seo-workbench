import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HelpTooltip } from "../components/HelpTooltip";

describe("HelpTooltip", () => {
  it("renders an accessible trigger with labelled tooltip content", () => {
    render(<HelpTooltip label="CTR benchmark">Internal benchmark.</HelpTooltip>);
    const trigger = screen.getByLabelText("Help: CTR benchmark");
    expect(trigger).toBeTruthy();
    expect(trigger.getAttribute("role")).toBe("img");
    expect(trigger.getAttribute("aria-describedby")).toBeTruthy();
    expect(screen.getByRole("tooltip").textContent).toBe("Internal benchmark.");
  });

  it("keeps long-form help structured with a lead-in and list", () => {
    render(<HelpTooltip label="Regimes"><><strong>Comparability guard.</strong><ul><li>Records changes that alter what a metric means.</li><li>A break makes the window incomparable.</li></ul></></HelpTooltip>);
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.querySelector("strong")?.textContent).toBe("Comparability guard.");
    expect(tooltip.querySelectorAll("li").length).toBe(2);
  });

  it("supports right-aligned bubbles for edge triggers", () => {
    render(<HelpTooltip label="Refresh analysis" align="right">Rebuilds this view from local evidence.</HelpTooltip>);
    expect(screen.getByLabelText("Help: Refresh analysis").getAttribute("class")).toContain("helpTooltipRight");
  });

  it("supports centered bubbles for card headings", () => {
    render(<HelpTooltip label="Click change decomposition" align="center">Explains the change.</HelpTooltip>);
    expect(screen.getByLabelText("Help: Click change decomposition").getAttribute("class")).toContain("helpTooltipCenter");
  });
});
