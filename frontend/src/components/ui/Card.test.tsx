import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Card from "./Card";

describe("Card", () => {
  it("renders its children", () => {
    render(<Card>카드 내용</Card>);
    expect(screen.getByText("카드 내용")).toBeInTheDocument();
  });

  it("does not assign an unnecessary ARIA role", () => {
    const { container } = render(<Card>카드 내용</Card>);
    const el = container.firstElementChild as HTMLElement;
    expect(el.getAttribute("role")).toBeNull();
  });
});
