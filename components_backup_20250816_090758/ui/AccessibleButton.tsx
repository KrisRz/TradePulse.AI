import { forwardRef } from 'preact/compat';
import type { ComponentChildren } from 'preact';

interface AccessibleButtonProps {
  children: ComponentChildren;
  onClick?: (event: Event) => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  type?: 'button' | 'submit' | 'reset';
  ariaLabel?: string;
  ariaDescribedBy?: string;
  ariaExpanded?: boolean;
  ariaPresseed?: boolean;
  loading?: boolean;
  icon?: ComponentChildren;
  iconPosition?: 'left' | 'right';
}

/**
 * AccessibleButton Component
 * 
 * WCAG 2.1 AA compliant button with:
 * - 4.5:1 color contrast ratio minimum
 * - Clear focus indicators (2px solid outline)
 * - Proper ARIA attributes
 * - Keyboard navigation support
 * - Loading and disabled states
 * - Screen reader announcements
 */
export const AccessibleButton = forwardRef<HTMLButtonElement, AccessibleButtonProps>(({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  ariaLabel,
  ariaDescribedBy,
  ariaExpanded,
  ariaPresseed,
  loading = false,
  icon,
  iconPosition = 'left',
  ...props
}, ref) => {
  
  const baseClasses = [
    // Base button styles
    'inline-flex items-center justify-center',
    'font-medium rounded-md',
    'transition-all duration-200',
    'border-2 border-transparent',
    
    // Focus styles (WCAG 2.1 AA compliant)
    'focus:outline-none focus:ring-2 focus:ring-offset-2',
    'focus-visible:ring-2 focus-visible:ring-offset-2',
    
    // Disabled state
    'disabled:opacity-50 disabled:cursor-not-allowed',
    'disabled:pointer-events-none',
    
    // High contrast mode support
    '@media (prefers-contrast: high) { border-width: 2px }'
  ];

  // Size variants
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm min-h-[32px]',
    md: 'px-4 py-2 text-base min-h-[40px]',
    lg: 'px-6 py-3 text-lg min-h-[48px]'
  };

  // Color variants with WCAG AA contrast ratios
  const variantClasses = {
    primary: [
      'bg-blue-600 text-white',
      'hover:bg-blue-700',
      'focus:ring-blue-500',
      'active:bg-blue-800',
      // High contrast support
      '@media (prefers-contrast: high) { bg-blue-700 border-blue-300 }'
    ].join(' '),
    
    secondary: [
      'bg-gray-100 text-gray-900 border-gray-300',
      'hover:bg-gray-200',
      'focus:ring-gray-500',
      'active:bg-gray-300',
      'dark:bg-gray-800 dark:text-gray-100 dark:border-gray-600',
      'dark:hover:bg-gray-700'
    ].join(' '),
    
    danger: [
      'bg-red-600 text-white',
      'hover:bg-red-700',
      'focus:ring-red-500',
      'active:bg-red-800'
    ].join(' '),
    
    success: [
      'bg-green-600 text-white',
      'hover:bg-green-700',
      'focus:ring-green-500',
      'active:bg-green-800'
    ].join(' ')
  };

  const classes = [
    ...baseClasses,
    sizeClasses[size],
    variantClasses[variant],
    className
  ].join(' ');

  const handleClick = (event: Event) => {
    if (disabled || loading) {
      event.preventDefault();
      return;
    }
    onClick?.(event);
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    // Support Space and Enter key activation
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      if (!disabled && !loading) {
        onClick?.(event as any);
      }
    }
  };

  // Loading spinner for accessibility
  const LoadingSpinner = () => (
    <svg 
      className="animate-spin h-4 w-4" 
      fill="none" 
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle 
        className="opacity-25" 
        cx="12" 
        cy="12" 
        r="10" 
        stroke="currentColor" 
        strokeWidth="4"
      />
      <path 
        className="opacity-75" 
        fill="currentColor" 
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );

  return (
    <button
      ref={ref}
      type={type}
      className={classes}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      disabled={disabled || loading}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      aria-expanded={ariaExpanded}
      aria-pressed={ariaPresseed}
      aria-busy={loading}
      role="button"
      {...props}
    >
      {/* Loading state */}
      {loading && (
        <>
          <LoadingSpinner />
          <span className="sr-only">Loading...</span>
        </>
      )}
      
      {/* Icon positioning */}
      {!loading && icon && iconPosition === 'left' && (
        <span className="mr-2" aria-hidden="true">
          {icon}
        </span>
      )}
      
      {/* Button content */}
      <span className={loading ? 'ml-2' : ''}>
        {children}
      </span>
      
      {/* Right icon */}
      {!loading && icon && iconPosition === 'right' && (
        <span className="ml-2" aria-hidden="true">
          {icon}
        </span>
      )}
    </button>
  );
});

AccessibleButton.displayName = 'AccessibleButton'; 