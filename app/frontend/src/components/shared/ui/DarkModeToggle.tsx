import { useState } from 'preact/hooks';
import { useTheme } from '../../contexts/ThemeContext';
import { clsx } from 'clsx';

interface DarkModeToggleProps {
  variant?: 'switch' | 'button' | 'icon' | 'dropdown';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
  iconOnly?: boolean;
}

export default function DarkModeToggle({
  variant = 'switch',
  size = 'md',
  showLabel = true,
  className = '',
  iconOnly = false,
}: DarkModeToggleProps) {
  const { theme, setTheme, resolvedTheme, systemPreference } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className={clsx(
        'animate-pulse rounded-full bg-gray-200 dark:bg-gray-700',
        size === 'sm' ? 'h-6 w-12' : size === 'lg' ? 'h-8 w-16' : 'h-7 w-14',
        className
      )} />
    );
  }

  const sizeClasses = {
    sm: {
      switch: 'h-6 w-12',
      button: 'px-2 py-1 text-sm',
      icon: 'h-6 w-6',
      toggle: 'h-4 w-4',
    },
    md: {
      switch: 'h-7 w-14',
      button: 'px-3 py-2 text-sm',
      icon: 'h-7 w-7',
      toggle: 'h-5 w-5',
    },
    lg: {
      switch: 'h-8 w-16',
      button: 'px-4 py-2 text-base',
      icon: 'h-8 w-8',
      toggle: 'h-6 w-6',
    },
  };

  const isDark = resolvedTheme === 'dark';

  // Switch variant
  if (variant === 'switch') {
    return (
      <div className={clsx('flex items-center space-x-3', className)}>
        {showLabel && !iconOnly && (
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Dark Mode
          </span>
        )}
        <button
          type="button"
          onClick={() => setTheme(isDark ? 'light' : 'dark')}
          className={clsx(
            'relative inline-flex items-center rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            sizeClasses[size].switch,
            isDark 
              ? 'bg-blue-600 hover:bg-blue-700' 
              : 'bg-gray-200 hover:bg-gray-300'
          )}
          role="switch"
          aria-checked={isDark}
          aria-label="Toggle dark mode"
        >
          <span
            className={clsx(
              'pointer-events-none relative inline-block rounded-full bg-white shadow-lg ring-0 transition-transform duration-200 ease-in-out',
              sizeClasses[size].toggle,
              isDark 
                ? 'translate-x-6' 
                : 'translate-x-1'
            )}
          >
            <span
              className={clsx(
                'absolute inset-0 flex items-center justify-center transition-opacity duration-200 ease-in-out',
                isDark ? 'opacity-0' : 'opacity-100'
              )}
            >
              <SunIcon className="h-3 w-3 text-yellow-500" />
            </span>
            <span
              className={clsx(
                'absolute inset-0 flex items-center justify-center transition-opacity duration-200 ease-in-out',
                isDark ? 'opacity-100' : 'opacity-0'
              )}
            >
              <MoonIcon className="h-3 w-3 text-blue-600" />
            </span>
          </span>
        </button>
      </div>
    );
  }

  // Button variant
  if (variant === 'button') {
    return (
      <button
        type="button"
        onClick={() => setTheme(isDark ? 'light' : 'dark')}
        className={clsx(
          'inline-flex items-center rounded-lg border border-gray-300 bg-white text-gray-700 shadow-sm transition-colors duration-200 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700',
          sizeClasses[size].button,
          className
        )}
        aria-label="Toggle dark mode"
      >
        {isDark ? (
          <SunIcon className={clsx('mr-2', sizeClasses[size].icon)} />
        ) : (
          <MoonIcon className={clsx('mr-2', sizeClasses[size].icon)} />
        )}
        {!iconOnly && (showLabel ? (isDark ? 'Light Mode' : 'Dark Mode') : '')}
      </button>
    );
  }

  // Icon variant
  if (variant === 'icon') {
    return (
      <button
        type="button"
        onClick={() => setTheme(isDark ? 'light' : 'dark')}
        className={clsx(
          'inline-flex items-center justify-center rounded-md p-2 text-gray-500 transition-colors duration-200 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-300',
          className
        )}
        aria-label="Toggle dark mode"
      >
        <span className="sr-only">Toggle dark mode</span>
        {isDark ? (
          <SunIcon className={sizeClasses[size].icon} />
        ) : (
          <MoonIcon className={sizeClasses[size].icon} />
        )}
      </button>
    );
  }

  // Dropdown variant
  if (variant === 'dropdown') {
    return (
      <div className={clsx('relative', className)}>
        <select
          value={theme}
          onChange={(e) => setTheme((e.target as HTMLInputElement).value as 'light' | 'dark' | 'system')}
          className={clsx(
            'block w-full rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300',
            sizeClasses[size].button
          )}
          aria-label="Select theme"
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="system">System</option>
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700 dark:text-gray-300">
          <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
            <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
          </svg>
        </div>
      </div>
    );
  }

  return null;
}

// Sun icon component
function SunIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
      />
    </svg>
  );
}

// Moon icon component
function MoonIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
      />
    </svg>
  );
} 