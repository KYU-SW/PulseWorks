import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PageHeader from "./PageHeader";

describe("PageHeader", () => {
  it("renders a real h1 with the title", () => {
    render(<PageHeader title="환자 목록" />);
    expect(screen.getByRole("heading", { level: 1, name: "환자 목록" })).toBeInTheDocument();
  });

  it("renders an optional description", () => {
    render(<PageHeader title="환자 목록" description="담당 환자 전체를 표시합니다." />);
    expect(screen.getByText("담당 환자 전체를 표시합니다.")).toBeInTheDocument();
  });

  it("renders optional actions", () => {
    render(<PageHeader title="환자 목록" actions={<button type="button">새로고침</button>} />);
    expect(screen.getByRole("button", { name: "새로고침" })).toBeInTheDocument();
  });

  it("keeps the title as one plain text node, not split into decorative spans", () => {
    render(<PageHeader title="환자 목록" />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toBe("환자 목록");
    expect(heading.querySelector("span")).toBeNull();
  });
});
