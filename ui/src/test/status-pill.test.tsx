import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusPill, statusLabel, statusTone } from "../components/StatusPill";

describe("shared status pill", () => {
  it("keeps HTTP response colors semantic", () => {
    render(<div><StatusPill value={200} context="http" /><StatusPill value={301} context="http" /><StatusPill value={404} context="http" /></div>);
    expect(screen.getByText("200").getAttribute("data-tone")).toBe("success");
    expect(screen.getByText("301").getAttribute("data-tone")).toBe("warning");
    expect(screen.getByText("404").getAttribute("data-tone")).toBe("danger");
  });

  it("shares evidence labels and tones", () => {
    expect(statusLabel("needs_auth")).toBe("Needs authentication");
    expect(statusTone("needs_auth", "evidence")).toBe("warning");
    expect(statusLabel("needs_tracking")).toBe("Needs tracking");
    expect(statusTone("needs_tracking", "evidence")).toBe("warning");
  });
});
