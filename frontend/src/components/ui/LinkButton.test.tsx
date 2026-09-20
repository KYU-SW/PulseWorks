import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import LinkButton from "./LinkButton";

describe("LinkButton", () => {
  it("renders a real link, not a button", () => {
    render(
      <MemoryRouter>
        <LinkButton to="/doctor">대시보드로</LinkButton>
      </MemoryRouter>
    );
    const link = screen.getByRole("link", { name: "대시보드로" });
    expect(link.tagName.toLowerCase()).toBe("a");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps the destination", () => {
    render(
      <MemoryRouter>
        <LinkButton to="/patient/reports">보고서 보기</LinkButton>
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: "보고서 보기" })).toHaveAttribute(
      "href",
      "/patient/reports"
    );
  });

  it("applies a visual variant class", () => {
    render(
      <MemoryRouter>
        <LinkButton to="/doctor" variant="secondary">
          이동
        </LinkButton>
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: "이동" }).className).toContain(
      "ui-button--secondary"
    );
  });
});
