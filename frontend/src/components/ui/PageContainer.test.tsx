import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PageContainer from "./PageContainer";

describe("PageContainer", () => {
  it("renders a real main element", () => {
    render(<PageContainer>내용</PageContainer>);
    expect(screen.getByRole("main").tagName.toLowerCase()).toBe("main");
  });

  it("renders its children", () => {
    render(<PageContainer>페이지 내용입니다</PageContainer>);
    expect(screen.getByText("페이지 내용입니다")).toBeInTheDocument();
  });
});
