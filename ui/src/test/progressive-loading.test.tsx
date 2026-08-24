import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProgressiveLoadingStatus, ProgressiveSkeletonRows } from "../components/ProgressiveLoading";

describe("progressive loading", () => {
  afterEach(() => vi.useRealTimers());

  it("renders a live status and table-sized skeleton rows", async () => {
    render(<><ProgressiveLoadingStatus loading complete={false} label="URLs" total={1247} /><table><tbody><ProgressiveSkeletonRows columns={[{ id: "url", width: "60%" }, { id: "status", width: "20%" }]} rows={3} /></tbody></table></>);

    expect((await screen.findByRole("status")).textContent).toContain("Loading URLs");
    expect(document.querySelectorAll("tbody tr")).toHaveLength(3);
    expect(document.querySelectorAll('[class*="skeletonCell"]')).toHaveLength(6);
  });

  it("renders notices as temporary floating statuses", () => {
    vi.useFakeTimers();
    const { rerender } = render(<ProgressiveLoadingStatus loading={false} complete label="keywords" notice="1 keyword updated." />);

    expect(screen.getByRole("status").textContent).toContain("1 keyword updated.");
    vi.advanceTimersByTime(1800);
    rerender(<ProgressiveLoadingStatus loading={false} complete label="keywords" />);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
