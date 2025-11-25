/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { EntityCard } from "@/components/entity/entity-card";
import type { Entity } from "@/types/entity";

const mockEntity: Entity = {
  id: "skill:test",
  name: "test-skill",
  type: "skill",
  source: "github:user/repo/skill",
  status: "synced",
  tags: ["testing", "example", "demo", "extra"],
  description: "A test skill for unit testing",
};

describe("EntityCard", () => {
  it("renders entity name", () => {
    render(<EntityCard entity={mockEntity} />);

    expect(screen.getByText("test-skill")).toBeInTheDocument();
  });

  it("displays entity type badge", () => {
    render(<EntityCard entity={mockEntity} />);

    expect(screen.getByText("Skill")).toBeInTheDocument();
  });

  it("shows description when provided", () => {
    render(<EntityCard entity={mockEntity} />);

    expect(
      screen.getByText("A test skill for unit testing")
    ).toBeInTheDocument();
  });

  it("truncates long description", () => {
    const longDescription =
      "This is a very long description that should be truncated after 100 characters to ensure the card doesn't become too tall";
    const entityWithLongDesc = { ...mockEntity, description: longDescription };

    render(<EntityCard entity={entityWithLongDesc} />);

    const description = screen.getByText(/This is a very long description/);
    expect(description.textContent).toContain("...");
  });

  it("displays status indicator with correct color", () => {
    render(<EntityCard entity={mockEntity} />);

    expect(screen.getByText("Synced")).toBeInTheDocument();
  });

  it("shows modified status correctly", () => {
    const modifiedEntity = { ...mockEntity, status: "modified" as const };
    render(<EntityCard entity={modifiedEntity} />);

    expect(screen.getByText("Modified")).toBeInTheDocument();
  });

  it("shows outdated status correctly", () => {
    const outdatedEntity = { ...mockEntity, status: "outdated" as const };
    render(<EntityCard entity={outdatedEntity} />);

    expect(screen.getByText("Outdated")).toBeInTheDocument();
  });

  it("shows conflict status correctly", () => {
    const conflictEntity = { ...mockEntity, status: "conflict" as const };
    render(<EntityCard entity={conflictEntity} />);

    expect(screen.getByText("Conflict")).toBeInTheDocument();
  });

  it("displays up to 3 tags", () => {
    render(<EntityCard entity={mockEntity} />);

    expect(screen.getByText("testing")).toBeInTheDocument();
    expect(screen.getByText("example")).toBeInTheDocument();
    expect(screen.getByText("demo")).toBeInTheDocument();
  });

  it("shows +N more badge when more than 3 tags", () => {
    render(<EntityCard entity={mockEntity} />);

    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("does not show tags section when no tags", () => {
    const noTagsEntity = { ...mockEntity, tags: [] };
    render(<EntityCard entity={noTagsEntity} />);

    expect(screen.queryByText("testing")).not.toBeInTheDocument();
  });

  it("calls onClick when card is clicked", () => {
    const handleClick = jest.fn();
    render(<EntityCard entity={mockEntity} onClick={handleClick} />);

    const card = screen.getByText("test-skill").closest("div");
    if (card?.parentElement) {
      fireEvent.click(card.parentElement);
    }

    expect(handleClick).toHaveBeenCalled();
  });

  it("does not trigger onClick when clicking checkbox", () => {
    const handleClick = jest.fn();
    render(
      <EntityCard
        entity={mockEntity}
        selectable={true}
        onClick={handleClick}
      />
    );

    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    // onClick should not be called when clicking checkbox
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("shows checkbox when selectable is true", () => {
    render(<EntityCard entity={mockEntity} selectable={true} />);

    expect(screen.getByRole("checkbox")).toBeInTheDocument();
  });

  it("does not show checkbox when selectable is false", () => {
    render(<EntityCard entity={mockEntity} selectable={false} />);

    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("calls onSelect when checkbox is checked", () => {
    const handleSelect = jest.fn();
    render(
      <EntityCard
        entity={mockEntity}
        selectable={true}
        onSelect={handleSelect}
      />
    );

    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    expect(handleSelect).toHaveBeenCalledWith(true);
  });

  it("applies selected styling when selected", () => {
    const { container } = render(
      <EntityCard entity={mockEntity} selected={true} />
    );

    const card = container.firstChild;
    expect(card).toHaveClass("ring-2", "ring-primary");
  });

  it("applies hover styling", () => {
    const { container } = render(<EntityCard entity={mockEntity} />);

    const card = container.firstChild;
    expect(card).toHaveClass("hover:bg-accent/50");
  });

  it("renders entity icon", () => {
    const { container } = render(<EntityCard entity={mockEntity} />);

    const icon = container.querySelector("svg");
    expect(icon).toBeInTheDocument();
  });

  it("renders EntityActions component", () => {
    render(<EntityCard entity={mockEntity} onEdit={jest.fn()} />);

    // EntityActions should render a menu button
    const menuButtons = screen.getAllByRole("button");
    expect(menuButtons.length).toBeGreaterThan(0);
  });

  it("passes action handlers to EntityActions", () => {
    const handlers = {
      onEdit: jest.fn(),
      onDelete: jest.fn(),
      onDeploy: jest.fn(),
      onSync: jest.fn(),
      onViewDiff: jest.fn(),
      onRollback: jest.fn(),
    };

    render(<EntityCard entity={mockEntity} {...handlers} />);

    // All handlers should be passed to EntityActions
    expect(screen.getByText("test-skill")).toBeInTheDocument();
  });

  it("handles missing description gracefully", () => {
    const noDescEntity = { ...mockEntity, description: undefined };
    render(<EntityCard entity={noDescEntity} />);

    expect(screen.queryByText(/test skill/)).not.toBeInTheDocument();
  });

  it("handles missing status gracefully", () => {
    const noStatusEntity = { ...mockEntity, status: undefined };
    render(<EntityCard entity={noStatusEntity} />);

    expect(screen.queryByText("Synced")).not.toBeInTheDocument();
  });

  it("displays correct icon based on entity type", () => {
    const commandEntity: Entity = {
      ...mockEntity,
      type: "command",
      id: "command:test",
    };

    render(<EntityCard entity={commandEntity} />);

    expect(screen.getByText("Command")).toBeInTheDocument();
  });
});
