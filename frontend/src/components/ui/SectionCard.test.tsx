import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SectionCard from "./SectionCard";

describe("SectionCard", () => {
  it("renders a real section element", () => {
    const { container } = render(<SectionCard title="검사결과">내용</SectionCard>);
    expect(container.querySelector("section")).not.toBeNull();
  });

  it("renders a heading and links it via aria-labelledby", () => {
    render(<SectionCard title="검사결과">내용</SectionCard>);
    const heading = screen.getByRole("heading", { name: "검사결과" });
    const section = screen.getByRole("region", { name: "검사결과" });
    expect(section.getAttribute("aria-labelledby")).toBe(heading.id);
  });

  it("renders its children", () => {
    render(<SectionCard title="검사결과">본문 텍스트</SectionCard>);
    expect(screen.getByText("본문 텍스트")).toBeInTheDocument();
  });

  it("supports a custom heading level", () => {
    render(
      <SectionCard title="세부 항목" headingLevel={3}>
        내용
      </SectionCard>
    );
    expect(screen.getByRole("heading", { level: 3, name: "세부 항목" })).toBeInTheDocument();
  });
});
