import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BasicInfoSection from '../BasicInfoSection';

describe('BasicInfoSection', () => {
  const defaultProps = {
    name: '',
    description: '',
    onNameChange: vi.fn(),
    onDescriptionChange: vi.fn(),
  };

  it('renders all form fields', () => {
    render(<BasicInfoSection {...defaultProps} />);
    
    expect(screen.getByLabelText(/task name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  it('calls onNameChange when name input changes', () => {
    const onNameChange = vi.fn();
    render(<BasicInfoSection {...defaultProps} onNameChange={onNameChange} />);
    
    const nameInput = screen.getByLabelText(/task name/i);
    fireEvent.change(nameInput, { target: { value: 'Test Task' } });
    
    expect(onNameChange).toHaveBeenCalledWith('Test Task');
  });

  it('calls onDescriptionChange when description changes', () => {
    const onDescriptionChange = vi.fn();
    render(<BasicInfoSection {...defaultProps} onDescriptionChange={onDescriptionChange} />);
    
    const descriptionInput = screen.getByLabelText(/description/i);
    fireEvent.change(descriptionInput, { target: { value: 'Test description' } });
    
    expect(onDescriptionChange).toHaveBeenCalledWith('Test description');
  });

  it('displays validation errors', () => {
    const errors = {
      name: 'Name is required',
      description: 'Description is too short',
    };
    
    render(<BasicInfoSection {...defaultProps} errors={errors} />);
    
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(screen.getByText('Description is too short')).toBeInTheDocument();
  });

  it('shows character count for description', () => {
    const description = 'Test description';
    render(<BasicInfoSection {...defaultProps} description={description} />);
    
    const remainingChars = 500 - description.length;
    expect(screen.getByText(`${remainingChars} characters remaining`)).toBeInTheDocument();
  });
});