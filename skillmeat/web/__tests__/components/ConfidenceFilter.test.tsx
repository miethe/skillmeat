import { render, screen, fireEvent } from '@testing-library/react';
import { ConfidenceFilter } from '@/components/ConfidenceFilter';

describe('ConfidenceFilter', () => {
  const mockProps = {
    minConfidence: 50,
    maxConfidence: 100,
    includeBelowThreshold: false,
    onMinChange: jest.fn(),
    onMaxChange: jest.fn(),
    onIncludeBelowThresholdChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders min and max confidence inputs', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const minInput = screen.getByLabelText('Minimum confidence score');
    const maxInput = screen.getByLabelText('Maximum confidence score');

    expect(minInput).toBeInTheDocument();
    expect(maxInput).toBeInTheDocument();
    expect(minInput).toHaveValue(50);
    expect(maxInput).toHaveValue(100);
  });

  it('renders below threshold checkbox', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const checkbox = screen.getByRole('checkbox', {
      name: /include low-confidence artifacts/i,
    });

    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  it('calls onMinChange when min input changes', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const minInput = screen.getByLabelText('Minimum confidence score');
    fireEvent.change(minInput, { target: { value: '60' } });

    expect(mockProps.onMinChange).toHaveBeenCalledWith(60);
  });

  it('calls onMaxChange when max input changes', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const maxInput = screen.getByLabelText('Maximum confidence score');
    fireEvent.change(maxInput, { target: { value: '90' } });

    expect(mockProps.onMaxChange).toHaveBeenCalledWith(90);
  });

  it('calls onIncludeBelowThresholdChange when checkbox is toggled', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const checkbox = screen.getByRole('checkbox', {
      name: /include low-confidence artifacts/i,
    });
    fireEvent.click(checkbox);

    expect(mockProps.onIncludeBelowThresholdChange).toHaveBeenCalledWith(true);
  });

  it('does not call onChange for invalid min values', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const minInput = screen.getByLabelText('Minimum confidence score');

    // Test invalid values
    fireEvent.change(minInput, { target: { value: '-10' } });
    expect(mockProps.onMinChange).not.toHaveBeenCalled();

    fireEvent.change(minInput, { target: { value: '150' } });
    expect(mockProps.onMinChange).not.toHaveBeenCalled();

    fireEvent.change(minInput, { target: { value: 'abc' } });
    expect(mockProps.onMinChange).not.toHaveBeenCalled();
  });

  it('does not call onChange for invalid max values', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const maxInput = screen.getByLabelText('Maximum confidence score');

    // Test invalid values
    fireEvent.change(maxInput, { target: { value: '-5' } });
    expect(mockProps.onMaxChange).not.toHaveBeenCalled();

    fireEvent.change(maxInput, { target: { value: '200' } });
    expect(mockProps.onMaxChange).not.toHaveBeenCalled();
  });

  it('applies custom className', () => {
    const { container } = render(<ConfidenceFilter {...mockProps} className="custom-class" />);

    const filterDiv = container.firstChild;
    expect(filterDiv).toHaveClass('custom-class');
  });

  it('renders with checked checkbox when includeBelowThreshold is true', () => {
    render(<ConfidenceFilter {...mockProps} includeBelowThreshold={true} />);

    const checkbox = screen.getByRole('checkbox', {
      name: /include low-confidence artifacts/i,
    });

    expect(checkbox).toBeChecked();
  });

  it('has proper accessibility attributes', () => {
    render(<ConfidenceFilter {...mockProps} />);

    const minInput = screen.getByLabelText('Minimum confidence score');
    const maxInput = screen.getByLabelText('Maximum confidence score');

    expect(minInput).toHaveAttribute('aria-describedby', 'confidence-help');
    expect(maxInput).toHaveAttribute('aria-describedby', 'confidence-help');
  });
});
