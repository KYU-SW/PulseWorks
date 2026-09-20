import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FormField from "./FormField";

describe("FormField", () => {
  it("connects the label to the input via htmlFor/id", () => {
    render(
      <FormField label="설명문" htmlFor="narrative-textarea">
        <textarea id="narrative-textarea" />
      </FormField>
    );
    expect(screen.getByLabelText("설명문")).toBeInTheDocument();
  });

  it("shows an optional description", () => {
    render(
      <FormField label="설명문" htmlFor="narrative-textarea" description="최대 10000자">
        <textarea id="narrative-textarea" />
      </FormField>
    );
    expect(screen.getByText("최대 10000자")).toBeInTheDocument();
  });

  it("shows an optional error", () => {
    render(
      <FormField label="설명문" htmlFor="narrative-textarea" error="필수 입력입니다.">
        <textarea id="narrative-textarea" />
      </FormField>
    );
    expect(screen.getByText("필수 입력입니다.")).toBeInTheDocument();
  });

  it("keeps the input child exactly as given", () => {
    render(
      <FormField label="설명문" htmlFor="narrative-textarea">
        <textarea id="narrative-textarea" defaultValue="기존 값" />
      </FormField>
    );
    expect(screen.getByLabelText("설명문")).toHaveValue("기존 값");
  });

  it("shows a required marker", () => {
    render(
      <FormField label="설명문" htmlFor="narrative-textarea" required>
        <textarea id="narrative-textarea" />
      </FormField>
    );
    expect(screen.getByText(/설명문/).textContent).toContain("*");
  });
});
