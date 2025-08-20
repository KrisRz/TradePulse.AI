import type { ComponentChildren } from 'preact';

interface SkipLinkProps {
  href: string;
  children: ComponentChildren;
  className?: string;
}

interface SkipLinksProps {
  links?: Array<{
    href: string;
    label: string;
  }>;
  className?: string;
}

/**
 * SkipLink Component
 * 
 * Individual skip link that appears on focus for keyboard navigation
 */
export function SkipLink({ href, children, className = '' }: SkipLinkProps) {
  const baseClasses = [
    // Positioning - hidden by default, visible on focus
    'absolute top-0 left-0 z-50',
    'transform -translate-y-full',
    'focus:translate-y-0',
    
    // Styling with high contrast
    'bg-blue-600 text-white',
    'px-4 py-2 text-sm font-medium',
    'border-2 border-blue-800',
    'rounded-md shadow-lg',
    
    // Focus styles
    'focus:outline-none focus:ring-2 focus:ring-white',
    'focus:ring-offset-2 focus:ring-offset-blue-600',
    
    // Smooth transitions
    'transition-transform duration-200 ease-in-out',
    
    // Ensure high contrast
    'hover:bg-blue-700 hover:border-blue-900',
    
    // Screen reader optimization
    'whitespace-nowrap'
  ];

  return (
    <a
      href={href}
      className={[...baseClasses, className].join(' ')}
      role="button"
      tabIndex={0}
    >
      {children}
    </a>
  );
}

/**
 * SkipLinks Component
 * 
 * WCAG 2.1 AA compliant skip navigation links for keyboard users
 * 
 * Default links for trading platform:
 * - Skip to main content
 * - Skip to trading controls
 * - Skip to portfolio summary
 * - Skip to notifications
 */
export function SkipLinks({ links, className = '' }: SkipLinksProps) {
  const defaultLinks = links || [
    { href: '#main-content', label: 'Skip to main content' },
    { href: '#trading-controls', label: 'Skip to trading controls' },
    { href: '#portfolio-summary', label: 'Skip to portfolio summary' },
    { href: '#live-prices', label: 'Skip to live prices' },
    { href: '#notifications', label: 'Skip to notifications' },
    { href: '#footer', label: 'Skip to footer' }
  ];

  return (
    <nav 
      className={`skip-links ${className}`}
      aria-label="Skip navigation links"
      role="navigation"
    >
      <div className="sr-only">
        Press Tab to access skip links for keyboard navigation
      </div>
      
      {defaultLinks.map((link, index) => (
        <SkipLink 
          key={`skip-${index}`}
          href={link.href}
        >
          {link.label}
        </SkipLink>
      ))}
    </nav>
  );
}

/**
 * MainContent Component
 * 
 * Wrapper for main content area with proper landmarks
 */
interface MainContentProps {
  children: ComponentChildren;
  className?: string;
  id?: string;
}

export function MainContent({ 
  children, 
  className = '',
  id = 'main-content'
}: MainContentProps) {
  return (
    <main
      id={id}
      className={className}
      role="main"
      aria-label="Main content"
      tabIndex={-1} // Allow programmatic focus
    >
      {children}
    </main>
  );
}

/**
 * SectionLandmark Component
 * 
 * Semantic section with proper ARIA landmarks
 */
interface SectionLandmarkProps {
  children: ComponentChildren;
  id: string;
  ariaLabel: string;
  className?: string;
  role?: 'region' | 'complementary' | 'navigation' | 'banner' | 'contentinfo';
}

export function SectionLandmark({
  children,
  id,
  ariaLabel,
  className = '',
  role = 'region'
}: SectionLandmarkProps) {
  return (
    <section
      id={id}
      className={className}
      role={role}
      aria-label={ariaLabel}
      tabIndex={-1} // Allow programmatic focus
    >
      {children}
    </section>
  );
}

/**
 * AccessibleHeading Component
 * 
 * Properly structured headings with correct hierarchy
 */
interface AccessibleHeadingProps {
  level: 1 | 2 | 3 | 4 | 5 | 6;
  children: ComponentChildren;
  className?: string;
  id?: string;
}

export function AccessibleHeading({
  level,
  children,
  className = '',
  id
}: AccessibleHeadingProps) {
  const Tag = `h${level}` as const;
  
  const baseClasses = [
    // Ensure headings are focusable for screen readers
    'focus:outline-none focus:ring-2 focus:ring-blue-500',
    'focus:ring-offset-2 rounded-sm',
    // Proper contrast and spacing
    'text-gray-900 dark:text-gray-100'
  ];

  return (
    <Tag
      id={id}
      className={[...baseClasses, className].join(' ')}
      tabIndex={-1}
    >
      {children}
    </Tag>
  );
} 