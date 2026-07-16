/**
 * Theme Configuration Utilities
 * Provides theme-aware styling utilities and class name helpers
 */

import { clsx, type ClassValue } from 'clsx';

// Utility function for conditional class names
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

// Theme-aware class configurations
export const themeClasses = {
  // Card styles
  card: {
    base: 'rounded-lg border shadow-sm',
    light: 'bg-white border-gray-200',
    dark: 'bg-gray-900 border-gray-800',
  },
  
  // Text styles
  text: {
    primary: {
      light: 'text-gray-900',
      dark: 'text-white',
    },
    secondary: {
      light: 'text-gray-600',
      dark: 'text-gray-400',
    },
    muted: {
      light: 'text-gray-500',
      dark: 'text-gray-500',
    },
  },
  
  // Background styles
  background: {
    primary: {
      light: 'bg-white',
      dark: 'bg-gray-900',
    },
    secondary: {
      light: 'bg-gray-50',
      dark: 'bg-gray-800',
    },
    muted: {
      light: 'bg-gray-100',
      dark: 'bg-gray-700',
    },
  },
  
  // Border styles
  border: {
    default: {
      light: 'border-gray-200',
      dark: 'border-gray-800',
    },
    muted: {
      light: 'border-gray-100',
      dark: 'border-gray-700',
    },
  },
} as const;

// Helper to get theme-aware classes
export function getThemeClasses(
  category: keyof typeof themeClasses,
  variant: string,
  theme: 'light' | 'dark' = 'light'
) {
  const categoryClasses = themeClasses[category] as any;
  const variantClasses = categoryClasses[variant];
  
  if (!variantClasses) return '';
  
  if (typeof variantClasses === 'string') {
    return variantClasses;
  }
  
  return variantClasses[theme] || '';
}

// Theme-aware component class builder
export function buildThemeClasses(
  baseClasses: string,
  themeVariants: {
    light?: string;
    dark?: string;
  },
  theme: 'light' | 'dark' = 'light'
) {
  return cn(
    baseClasses,
    theme === 'dark' ? themeVariants.dark : themeVariants.light
  );
}

export default {
  cn,
  themeClasses,
  getThemeClasses,
  buildThemeClasses,
};
