/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ArtifactTypeTabs } from '@/components/shared/artifact-type-tabs';

describe('ArtifactTypeTabs', () => {
  it('renders all tab first and selected by default', () => {
    render(<ArtifactTypeTabs value="all" onChange={jest.fn()} />);

    const allTab = screen.getByRole('tab', { name: /All/ });
    expect(allTab).toHaveAttribute('data-state', 'active');
  });

  it('invokes onChange when selecting a specific type', async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();

    render(<ArtifactTypeTabs value="all" onChange={onChange} />);
    await user.click(screen.getByRole('tab', { name: /Skills/ }));

    expect(onChange).toHaveBeenCalledWith('skill');
  });
});
