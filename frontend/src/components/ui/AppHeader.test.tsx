import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AppHeader from "./AppHeader";

describe("AppHeader", () => {
  it("renders a real header element", () => {
    render(<AppHeader />);
    expect(screen.getByRole("banner").tagName.toLowerCase()).toBe("header");
  });

  it("renders the brand and actions slots", () => {
    render(
      <AppHeader brand={<span>EMR</span>} actions={<button type="button">로그아웃</button>}>
        <nav aria-label="주요 내비게이션" />
      </AppHeader>
    );

    expect(screen.getByText("EMR")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "로그아웃" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "주요 내비게이션" })).toBeInTheDocument();
  });
});
