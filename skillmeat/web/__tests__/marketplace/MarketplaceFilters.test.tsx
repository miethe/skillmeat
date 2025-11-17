/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { MarketplaceFilters } from "@/components/marketplace/MarketplaceFilters";
import type { MarketplaceFilters as Filters } from "@/types/marketplace";

const mockBrokers = [
  { name: "skillmeat", enabled: true },
  { name: "claudehub", enabled: true },
  { name: "disabled-broker", enabled: false },
];

describe("MarketplaceFilters", () => {
  it("renders search input", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    expect(
      screen.getByPlaceholderText("Search marketplace listings...")
    ).toBeInTheDocument();
  });

  it("calls onFiltersChange when search input changes", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    const searchInput = screen.getByPlaceholderText("Search marketplace listings...");
    fireEvent.change(searchInput, { target: { value: "test query" } });

    expect(handleChange).toHaveBeenCalledWith({ query: "test query" });
  });

  it("displays enabled brokers only", () => {
    const handleChange = jest.fn();
    render(
      <MarketplaceFilters
        filters={{}}
        onFiltersChange={handleChange}
        brokers={mockBrokers}
      />
    );

    const brokerSelect = screen.getByLabelText("Broker");
    expect(brokerSelect).toBeInTheDocument();

    // Check that enabled brokers are present
    expect(screen.getByRole("option", { name: "skillmeat" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "claudehub" })).toBeInTheDocument();

    // Check that disabled broker is not present
    expect(screen.queryByRole("option", { name: "disabled-broker" })).not.toBeInTheDocument();
  });

  it("calls onFiltersChange when license filter changes", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    const licenseSelect = screen.getByLabelText("License");
    fireEvent.change(licenseSelect, { target: { value: "MIT" } });

    expect(handleChange).toHaveBeenCalledWith({ license: "MIT" });
  });

  it("adds tag when Add button is clicked", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    const tagInput = screen.getByLabelText("Tags");
    const addButton = screen.getByRole("button", { name: "Add" });

    fireEvent.change(tagInput, { target: { value: "python" } });
    fireEvent.click(addButton);

    expect(handleChange).toHaveBeenCalledWith({ tags: ["python"] });
  });

  it("adds tag when Enter key is pressed", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    const tagInput = screen.getByLabelText("Tags");

    fireEvent.change(tagInput, { target: { value: "testing" } });
    fireEvent.keyDown(tagInput, { key: "Enter" });

    expect(handleChange).toHaveBeenCalledWith({ tags: ["testing"] });
  });

  it("removes tag when X button is clicked", () => {
    const handleChange = jest.fn();
    const filters: Filters = { tags: ["python", "testing"] };

    render(<MarketplaceFilters filters={filters} onFiltersChange={handleChange} />);

    const removeButton = screen.getByLabelText("Remove tag: python");
    fireEvent.click(removeButton);

    expect(handleChange).toHaveBeenCalledWith({ tags: ["testing"] });
  });

  it("adds suggested tag when clicked", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    // Find and click a suggested tag
    const suggestedTag = screen.getByRole("button", { name: "testing" });
    fireEvent.click(suggestedTag);

    expect(handleChange).toHaveBeenCalledWith({ tags: ["testing"] });
  });

  it("shows active filter count", () => {
    const handleChange = jest.fn();
    const filters: Filters = {
      query: "test",
      license: "MIT",
      tags: ["python"],
    };

    render(<MarketplaceFilters filters={filters} onFiltersChange={handleChange} />);

    expect(screen.getByText("3 filters active")).toBeInTheDocument();
  });

  it("clears all filters when Clear all is clicked", () => {
    const handleChange = jest.fn();
    const filters: Filters = {
      query: "test",
      license: "MIT",
      tags: ["python"],
    };

    render(<MarketplaceFilters filters={filters} onFiltersChange={handleChange} />);

    const clearButton = screen.getByRole("button", { name: "Clear all filters" });
    fireEvent.click(clearButton);

    expect(handleChange).toHaveBeenCalledWith({});
  });

  it("does not show Clear all button when no filters are active", () => {
    const handleChange = jest.fn();
    render(<MarketplaceFilters filters={{}} onFiltersChange={handleChange} />);

    expect(screen.queryByRole("button", { name: "Clear all filters" })).not.toBeInTheDocument();
  });
});
