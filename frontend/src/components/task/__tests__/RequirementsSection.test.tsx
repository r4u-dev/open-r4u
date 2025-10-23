import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import RequirementsSection from '../RequirementsSection';

describe('RequirementsSection', () => {
  const defaultProps = {
    requirements: '',
    onRequirementsChange: vi.fn(),
  };

  it('renders edit and preview tabs', () => {
    render(<RequirementsSection {...defaultProps} />);
    
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();
  });

  it('calls onRequirementsChange when text changes', () => {
    const onRequirementsChange = vi.fn();
    render(<RequirementsSection {...defaultProps} onRequirementsChange={onRequirementsChange} />);
    
    const textarea = screen.getByPlaceholderText(/define the task requirements/i);
    fireEvent.change(textarea, { target: { value: 'Test requirements' } });
    
    expect(onRequirementsChange).toHaveBeenCalledWith('Test requirements');
  });

  it('inserts template when template button is clicked', () => {
    const onRequirementsChange = vi.fn();
    render(<RequirementsSection {...defaultProps} onRequirementsChange={onRequirementsChange} />);
    
    const templateButton = screen.getByText('Insert Template');
    fireEvent.click(templateButton);
    
    expect(onRequirementsChange).toHaveBeenCalledWith(
      expect.stringContaining('# Task Requirements')
    );
  });

  it('allows switching between edit and preview tabs', () => {
    const requirements = '# Test Header\n\nThis is a test paragraph.';
    render(<RequirementsSection {...defaultProps} requirements={requirements} />);
    
    // Check that both tabs are present and clickable
    const editTab = screen.getByRole('tab', { name: /edit/i });
    const previewTab = screen.getByRole('tab', { name: /preview/i });
    
    expect(editTab).toBeInTheDocument();
    expect(previewTab).toBeInTheDocument();
    
    // Test that tabs are clickable (no errors thrown)
    fireEvent.click(previewTab);
    fireEvent.click(editTab);
  });

  it('has accessible tab structure', () => {
    render(<RequirementsSection {...defaultProps} />);
    
    // Check that tabs are properly structured
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /preview/i })).toBeInTheDocument();
    expect(screen.getByRole('tabpanel')).toBeInTheDocument();
  });

  it('displays validation errors', () => {
    const errors = { requirements: 'Requirements are required' };
    render(<RequirementsSection {...defaultProps} errors={errors} />);
    
    expect(screen.getByText('Requirements are required')).toBeInTheDocument();
  });

  it('shows character count', () => {
    const requirements = 'Test requirements';
    render(<RequirementsSection {...defaultProps} requirements={requirements} />);
    
    const remainingChars = 5000 - requirements.length;
    expect(screen.getByText(`${remainingChars} characters remaining`)).toBeInTheDocument();
  });
});