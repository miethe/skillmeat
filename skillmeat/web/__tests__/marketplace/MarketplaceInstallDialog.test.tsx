/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { MarketplaceInstallDialog } from "@/components/marketplace/MarketplaceInstallDialog";
import type { MarketplaceListing } from "@/types/marketplace";

const mockListing: MarketplaceListing = {
  listing_id: "test-listing-123",
  name: "Test Bundle",
  publisher: "Test Publisher",
  license: "MIT",
  artifact_count: 5,
  tags: ["testing"],
  created_at: "2025-01-15T10:00:00Z",
  source_url: "https://marketplace.test/listings/123",
  price: 0,
};

describe("MarketplaceInstallDialog", () => {
  it("renders dialog when open", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    expect(screen.getByText("Install Bundle")).toBeInTheDocument();
    expect(screen.getByText(/Install Test Bundle from Test Publisher/i)).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={false}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    expect(screen.queryByText("Install Bundle")).not.toBeInTheDocument();
  });

  it("displays bundle information", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    expect(screen.getByText("5 items")).toBeInTheDocument();
    expect(screen.getByText("Test Publisher")).toBeInTheDocument();
    expect(screen.getByText("MIT")).toBeInTheDocument();
  });

  it("displays trust warning", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    expect(screen.getByText("Trust Verification")).toBeInTheDocument();
    expect(
      screen.getByText(/This bundle is signed and verified/i)
    ).toBeInTheDocument();
  });

  it("allows selecting merge strategy", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    const strategySelect = screen.getByLabelText("Conflict Resolution Strategy");
    fireEvent.change(strategySelect, { target: { value: "merge" } });

    expect(strategySelect).toHaveValue("merge");
    expect(
      screen.getByText("Existing artifacts will be updated with new versions.")
    ).toBeInTheDocument();
  });

  it("allows selecting fork strategy", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    const strategySelect = screen.getByLabelText("Conflict Resolution Strategy");
    fireEvent.change(strategySelect, { target: { value: "fork" } });

    expect(strategySelect).toHaveValue("fork");
    expect(
      screen.getByText("Conflicts will be resolved by creating renamed copies.")
    ).toBeInTheDocument();
  });

  it("allows selecting skip strategy", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    const strategySelect = screen.getByLabelText("Conflict Resolution Strategy");
    fireEvent.change(strategySelect, { target: { value: "skip" } });

    expect(strategySelect).toHaveValue("skip");
    expect(
      screen.getByText("Existing artifacts will be left unchanged.")
    ).toBeInTheDocument();
  });

  it("calls onConfirm with selected strategy when Install button is clicked", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    const strategySelect = screen.getByLabelText("Conflict Resolution Strategy");
    fireEvent.change(strategySelect, { target: { value: "fork" } });

    const installButton = screen.getByRole("button", { name: /Install Bundle/i });
    fireEvent.click(installButton);

    expect(handleConfirm).toHaveBeenCalledWith("fork");
  });

  it("calls onClose when Cancel button is clicked", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
      />
    );

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    fireEvent.click(cancelButton);

    expect(handleClose).toHaveBeenCalled();
  });

  it("shows loading state when installing", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
        isInstalling={true}
      />
    );

    expect(screen.getByText("Installing...")).toBeInTheDocument();

    const installButton = screen.getByRole("button", { name: /Installing/i });
    expect(installButton).toBeDisabled();

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    expect(cancelButton).toBeDisabled();
  });

  it("disables strategy selector when installing", () => {
    const handleClose = jest.fn();
    const handleConfirm = jest.fn();

    render(
      <MarketplaceInstallDialog
        listing={mockListing}
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
        isInstalling={true}
      />
    );

    const strategySelect = screen.getByLabelText("Conflict Resolution Strategy");
    expect(strategySelect).toBeDisabled();
  });
});
