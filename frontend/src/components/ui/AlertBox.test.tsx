import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AlertBox from "./AlertBox";

describe("AlertBox", () => {
  it("supports role=alert for a real error", () => {
    render(
      <AlertBox variant="error" role="alert" title="오류">
        문제가 발생했습니다.
      </AlertBox>
    );
    expect(screen.getByRole("alert")).toHaveTextContent("문제가 발생했습니다.");
  });

  it("does not force role=alert for a normal info notice", () => {
    render(
      <AlertBox variant="info" title="안내">
        참고 정보입니다.
      </AlertBox>
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the title and children as text", () => {
    render(
      <AlertBox variant="warning" title="주의">
        확인이 필요합니다.
      </AlertBox>
    );
    expect(screen.getByText("주의")).toBeInTheDocument();
    expect(screen.getByText("확인이 필요합니다.")).toBeInTheDocument();
  });

  it("applies a variant class", () => {
    const { container } = render(<AlertBox variant="success">완료되었습니다.</AlertBox>);
    expect(container.firstElementChild?.className).toContain("ui-alert--success");
  });
});
