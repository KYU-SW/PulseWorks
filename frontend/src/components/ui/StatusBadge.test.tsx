import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatusBadge from "./StatusBadge";

describe("StatusBadge", () => {
  it.each([
    ["DRAFT", "초안"],
    ["APPROVED", "승인됨"],
    ["REJECTED", "반려됨"],
  ])("shows the report label for %s", (status, label) => {
    render(<StatusBadge kind="report" status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it.each([
    ["LOW", "낮음"],
    ["NORMAL", "정상"],
    ["HIGH", "높음"],
    ["UNKNOWN", "판정불가"],
  ])("shows the lab label for %s", (status, label) => {
    render(<StatusBadge kind="lab" status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("hides the visual dot from the accessibility tree", () => {
    const { container } = render(<StatusBadge kind="lab" status="HIGH" />);
    const dot = container.querySelector(".ui-status-badge__dot");
    expect(dot).toHaveAttribute("aria-hidden", "true");
  });

  it("always shows the text label, not color alone", () => {
    render(<StatusBadge kind="report" status="APPROVED" />);
    expect(screen.getByText("승인됨")).toBeVisible();
  });

  it("falls back to a safe label for an unrecognized status instead of showing the raw value", () => {
    render(<StatusBadge kind="lab" status="WEIRD_UNKNOWN_CODE" />);
    expect(screen.getByText("알 수 없음")).toBeInTheDocument();
    expect(screen.queryByText("WEIRD_UNKNOWN_CODE")).not.toBeInTheDocument();
  });
});
