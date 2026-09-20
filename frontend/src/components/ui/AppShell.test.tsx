import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AppShell from "./AppShell";

describe("AppShell", () => {
  it("renders the passed header and a main landmark for children", () => {
    render(
      <AppShell header={<header>테스트 헤더</header>}>
        <p>페이지 본문</p>
      </AppShell>
    );

    expect(screen.getByRole("banner")).toHaveTextContent("테스트 헤더");
    expect(screen.getByRole("main")).toHaveTextContent("페이지 본문");
  });

  it("renders children", () => {
    render(<AppShell>본문 내용</AppShell>);
    expect(screen.getByText("본문 내용")).toBeInTheDocument();
  });

  it("shows the synthetic-data notice when requested", () => {
    render(<AppShell showSyntheticDataNotice>본문</AppShell>);
    expect(
      screen.getByText(
        "이 시스템은 교육용 합성 데이터를 사용합니다. 실제 진료에 사용할 수 없습니다."
      )
    ).toBeInTheDocument();
  });

  it("does not show the notice by default", () => {
    render(<AppShell>본문</AppShell>);
    expect(
      screen.queryByText(/교육용 합성 데이터를 사용합니다/)
    ).not.toBeInTheDocument();
  });

  it("never gives the normal synthetic-data notice role=alert", () => {
    render(<AppShell showSyntheticDataNotice>본문</AppShell>);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
