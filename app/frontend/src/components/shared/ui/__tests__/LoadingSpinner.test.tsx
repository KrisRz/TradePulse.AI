import { render, screen } from '@testing-library/preact';
import LoadingSpinner from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default props', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass('h-6 w-6'); // Default medium size
    expect(spinner).toHaveClass('text-blue-600'); // Default primary color
  });

  it('renders with small size', () => {
    render(<LoadingSpinner size="sm" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('h-4 w-4');
  });

  it('renders with large size', () => {
    render(<LoadingSpinner size="lg" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('h-8 w-8');
  });

  it('renders with extra large size', () => {
    render(<LoadingSpinner size="xl" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('h-12 w-12');
  });

  it('renders with white color', () => {
    render(<LoadingSpinner color="white" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('text-white');
  });

  it('renders with gray color', () => {
    render(<LoadingSpinner color="gray" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('text-gray-600');
  });

  it('applies custom className', () => {
    render(<LoadingSpinner className="custom-class" />);
    
    const container = screen.getByRole('status').parentElement;
    expect(container).toHaveClass('custom-class');
  });

  it('has animate-spin class for animation', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('animate-spin');
  });

  it('has correct SVG structure', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    const svg = spinner.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('viewBox', '0 0 24 24');
    expect(svg).toHaveAttribute('fill', 'none');
    
    // Check for circle and path elements
    const circle = svg?.querySelector('circle');
    const path = svg?.querySelector('path');
    expect(circle).toBeInTheDocument();
    expect(path).toBeInTheDocument();
  });

  it('combines size and color classes correctly', () => {
    render(<LoadingSpinner size="lg" color="white" />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('h-8 w-8');
    expect(spinner).toHaveClass('text-white');
    expect(spinner).toHaveClass('animate-spin');
  });

  it('maintains accessibility with proper role', () => {
    render(<LoadingSpinner />);
    
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
  });
}); 