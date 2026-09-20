import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Button from "./Button";

describe("Button", () => {
  it("renders a real button element", () => {
    render(<Button>저장</Button>);
    expect(screen.getByRole("button", { name: "저장" }).tagName.toLowerCase()).toBe("button");
  });

  it("defaults to type=button", () => {
    render(<Button>저장</Button>);
    expect(screen.getByRole("button", { name: "저장" })).toHaveAttribute("type", "button");
  });

  it("applies a variant class", () => {
    render(<Button variant="danger">삭제</Button>);
    expect(screen.getByRole("button", { name: "삭제" }).className).toContain("ui-button--danger");
  });

  it("can be disabled", () => {
    render(<Button disabled>저장</Button>);
    expect(screen.getByRole("button", { name: "저장" })).toBeDisabled();
  });

  it("is disabled while loading", () => {
    render(<Button loading>저장</Button>);
    expect(screen.getByRole("button", { name: "저장" })).toBeDisabled();
  });

  it("marks a loading button aria-busy without losing its accessible name", () => {
    render(<Button loading>저장</Button>);
    const button = screen.getByRole("button", { name: "저장" });
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>저장</Button>);
    screen.getByRole("button", { name: "저장" }).click();
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
