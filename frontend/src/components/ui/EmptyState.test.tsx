import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EmptyState from "./EmptyState";

describe("EmptyState", () => {
  it("shows the normal empty-state title", () => {
    render(<EmptyState title="현재 확인할 수 있는 승인 보고서가 없습니다." />);
    expect(
      screen.getByText("현재 확인할 수 있는 승인 보고서가 없습니다.")
    ).toBeInTheDocument();
  });

  it("is not an alert", () => {
    render(<EmptyState title="표시할 항목이 없습니다." />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders an optional action", () => {
    render(
      <EmptyState title="표시할 항목이 없습니다." action={<button type="button">새로고침</button>} />
    );
    expect(screen.getByRole("button", { name: "새로고침" })).toBeInTheDocument();
  });
});
