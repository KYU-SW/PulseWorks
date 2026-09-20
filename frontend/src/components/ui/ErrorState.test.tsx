import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ErrorState from "./ErrorState";

describe("ErrorState", () => {
  it("has role=alert", () => {
    render(<ErrorState title="오류가 발생했습니다." />);
    expect(screen.getByRole("alert")).toHaveTextContent("오류가 발생했습니다.");
  });

  it("renders a retry button with a clear accessible name when onRetry is given", () => {
    render(<ErrorState title="오류가 발생했습니다." onRetry={() => {}} />);
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
  });

  it("renders no button when onRetry is not given", () => {
    render(<ErrorState title="오류가 발생했습니다." />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("calls onRetry when the retry button is clicked", async () => {
    const onRetry = vi.fn();
    render(<ErrorState title="오류" onRetry={onRetry} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "다시 시도" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
