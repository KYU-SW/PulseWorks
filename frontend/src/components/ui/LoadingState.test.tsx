import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoadingState from "./LoadingState";

describe("LoadingState", () => {
  it("shows the loading text", () => {
    render(<LoadingState label="보고서를 불러오는 중..." />);
    expect(screen.getByText("보고서를 불러오는 중...")).toBeInTheDocument();
  });

  it("is not an error role", () => {
    render(<LoadingState label="불러오는 중..." />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
