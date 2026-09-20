import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DataTable from "./DataTable";

describe("DataTable", () => {
  it("preserves the wrapped table's role and content", () => {
    render(
      <DataTable>
        <table>
          <thead>
            <tr>
              <th scope="col">검사명</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>HbA1c</td>
            </tr>
          </tbody>
        </table>
      </DataTable>
    );

    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "검사명" })).toBeInTheDocument();
    expect(screen.getByText("HbA1c")).toBeInTheDocument();
  });

  it("wraps the table in a scroll container class", () => {
    const { container } = render(
      <DataTable>
        <table>
          <tbody>
            <tr>
              <td>값</td>
            </tr>
          </tbody>
        </table>
      </DataTable>
    );
    expect(container.firstElementChild?.className).toContain("ui-table-scroll");
  });

  it("does not add a redundant table role to the wrapper", () => {
    const { container } = render(
      <DataTable>
        <table>
          <tbody>
            <tr>
              <td>값</td>
            </tr>
          </tbody>
        </table>
      </DataTable>
    );
    expect(container.firstElementChild?.getAttribute("role")).not.toBe("table");
  });
});
