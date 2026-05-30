import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressRing } from "@/components/ProgressRing";

describe("ProgressRing", () => {
  it("clamps progress values for display", () => {
    render(<ProgressRing value={140} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});
