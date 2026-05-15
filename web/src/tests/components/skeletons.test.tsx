import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import {
  CardSkeleton,
  ChartSkeleton,
  TableSkeleton,
} from "@/components/skeletons";

describe("skeleton components", () => {
  it("renders CardSkeleton and accepts className", () => {
    render(<CardSkeleton className="extra-card" />);
    const node = screen.getByTestId("card-skeleton");
    expect(node).toBeInTheDocument();
    expect(node.className).toContain("extra-card");
  });

  it("renders ChartSkeleton with custom height", () => {
    render(<ChartSkeleton height={240} />);
    const node = screen.getByTestId("chart-skeleton");
    expect(node).toBeInTheDocument();
    expect(node).toHaveStyle({ height: "240px" });
  });

  it("renders TableSkeleton with configured rows and columns", () => {
    render(<TableSkeleton rows={3} columns={2} />);
    expect(screen.getAllByTestId("table-skeleton-row")).toHaveLength(3);
    expect(screen.getAllByTestId("table-skeleton-cell")).toHaveLength(6);
  });
});
