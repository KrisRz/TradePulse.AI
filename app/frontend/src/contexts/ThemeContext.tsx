import { createContext } from 'preact';
import { useContext, useEffect, useState, useCallback } from 'preact/hooks';

export type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  systemPreference: 'light' | 'dark';
}

const ThemeContext = createContext<ThemeContextType | null>(null);

interface ThemeProviderProps {
  children: preact.ComponentChildren;
  defaultTheme?: Theme;
  storageKey?: string;
  enableSystem?: boolean;
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'theme',
  enableSystem = true,
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme);
  const [systemPreference, setSystemPreference] = useState<'light' | 'dark'>('light');
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');

  // Get system preference
  const getSystemPreference = useCallback((): 'light' | 'dark' => {
    if (typeof window === 'undefined') return 'light';
    
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }, []);

  // Resolve theme based on current theme and system preference
  const resolveTheme = useCallback((currentTheme: Theme): 'light' | 'dark' => {
    if (currentTheme === 'system') {
      return systemPreference;
    }
    return currentTheme;
  }, [systemPreference]);

  // Apply theme to document
  const applyTheme = useCallback((resolvedTheme: 'light' | 'dark') => {
    if (typeof window === 'undefined') return;

    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light', 'dark');
    
    // Add new theme class
    root.classList.add(resolvedTheme);
    
    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content',
        resolvedTheme === 'dark' ? '#1f2937' : '#ffffff'
      );
    }

    // Update CSS custom properties for dynamic theming
    const styles = getComputedStyle(root);
    const isDark = resolvedTheme === 'dark';
    
    // These can be used for dynamic theming without Tailwind classes
    root.style.setProperty('--theme-bg', isDark ? '#1f2937' : '#ffffff');
    root.style.setProperty('--theme-fg', isDark ? '#ffffff' : '#1f2937');
    root.style.setProperty('--theme-primary', isDark ? '#3b82f6' : '#2563eb');
  }, []);

  // Initialize theme from storage or system preference
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const savedTheme = localStorage.getItem(storageKey) as Theme;
    const systemPref = getSystemPreference();
    
    setSystemPreference(systemPref);

    if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
      setThemeState(savedTheme);
    } else {
      setThemeState(defaultTheme);
    }
  }, [storageKey, defaultTheme, getSystemPreference]);

  // Update resolved theme when theme or system preference changes
  useEffect(() => {
    const resolved = resolveTheme(theme);
    setResolvedTheme(resolved);
    applyTheme(resolved);
  }, [theme, resolveTheme, applyTheme]);

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window === 'undefined' || !enableSystem) return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      const newSystemPreference = e.matches ? 'dark' : 'light';
      setSystemPreference(newSystemPreference);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } 
    // Legacy browsers
    else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, [enableSystem]);

  // Set theme and persist to storage
  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    
    if (typeof window !== 'undefined') {
      localStorage.setItem(storageKey, newTheme);
    }
  }, [storageKey]);

  // Toggle between light and dark (ignoring system)
  const toggleTheme = useCallback(() => {
    const newTheme = resolvedTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
  }, [resolvedTheme, setTheme]);

  // Prevent hydration mismatch by not rendering until mounted
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <>{children}</>;
  }

  const contextValue: ThemeContextType = {
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
    systemPreference,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// Hook for components that need to detect dark mode
export function useDarkMode(): boolean {
  const { resolvedTheme } = useTheme();
  return resolvedTheme === 'dark';
}

// Hook for getting theme-aware classes
export function useThemeClasses() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  
  return {
    isDark,
    bg: isDark ? 'bg-gray-900' : 'bg-white',
    bgSecondary: isDark ? 'bg-gray-800' : 'bg-gray-50',
    text: isDark ? 'text-white' : 'text-gray-900',
    textSecondary: isDark ? 'text-gray-300' : 'text-gray-600',
    textMuted: isDark ? 'text-gray-500' : 'text-gray-400',
    border: isDark ? 'border-gray-700' : 'border-gray-200',
    borderSecondary: isDark ? 'border-gray-600' : 'border-gray-300',
    hover: isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-100',
    active: isDark ? 'active:bg-gray-700' : 'active:bg-gray-200',
    focus: 'focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
    focusVisible: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
  };
}

export default ThemeContext; 