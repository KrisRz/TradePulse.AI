# 🌙 Dark Mode Implementation Guide

This guide covers the comprehensive dark mode system implemented in TradePulse.AI frontend.

## 🎯 Features

- **System Preference Detection** - Automatically detects user's OS theme preference
- **Manual Toggle** - Users can override system preference
- **Persistent Storage** - Remembers user's choice across sessions
- **Theme Variants** - Multiple toggle components (switch, button, icon, dropdown)
- **Smooth Transitions** - Animated theme switching
- **TypeScript Support** - Full type safety
- **SSR Compatible** - Works with Astro static generation

## 🏗️ Architecture

### Core Components

1. **ThemeContext** (`src/contexts/ThemeContext.tsx`)
   - Manages theme state and system preference detection
   - Provides theme utilities and resolved theme values
   - Handles localStorage persistence

2. **DarkModeToggle** (`src/components/ui/DarkModeToggle.tsx`)
   - Multiple variants: switch, button, icon, dropdown
   - Customizable sizes and styling
   - Accessibility support

3. **Theme Configuration** (`src/lib/theme-config.ts`)
   - Centralized theme classes and utilities
   - Trading-specific color schemes
   - Chart color configurations

4. **App Layout** (`src/components/layout/AppLayout.tsx`)
   - Integrates theme with authentication
   - Provides consistent app structure
   - Theme-aware navigation and footer

## 🚀 Quick Start

### 1. Wrap Your App

```tsx
import { ThemeProvider } from '../contexts/ThemeContext';

export default function App() {
  return (
    <ThemeProvider defaultTheme="system" enableSystem={true}>
      <YourAppContent />
    </ThemeProvider>
  );
}
```

### 2. Add Dark Mode Toggle

```tsx
import DarkModeToggle from '../components/ui/DarkModeToggle';

export default function Header() {
  return (
    <header>
      <h1>TradePulse.AI</h1>
      <DarkModeToggle variant="switch" size="md" />
    </header>
  );
}
```

### 3. Use Theme Classes

```tsx
import { useTheme } from '../contexts/ThemeContext';

export default function Card() {
  const { resolvedTheme } = useTheme();
  
  return (
    <div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
      <h2>Current theme: {resolvedTheme}</h2>
    </div>
  );
}
```

## 🎨 Theme System

### Available Hooks

#### `useTheme()`
```tsx
const { 
  theme,           // 'light' | 'dark' | 'system'
  resolvedTheme,   // 'light' | 'dark' (actual theme)
  setTheme,        // Function to set theme
  toggleTheme,     // Function to toggle between light/dark
  systemPreference // System's preferred theme
} = useTheme();
```

#### `useDarkMode()`
```tsx
const isDark = useDarkMode(); // boolean
```

#### `useThemeClasses()`
```tsx
const { 
  isDark,
  bg,              // 'bg-gray-900' or 'bg-white'
  text,            // 'text-white' or 'text-gray-900'
  border,          // 'border-gray-700' or 'border-gray-200'
  // ... more theme-aware classes
} = useThemeClasses();
```

### Pre-built Theme Classes

```tsx
import { themeClasses } from '../lib/theme-config';

// Button variants
<button className={themeClasses.button.primary}>
  Primary Button
</button>

// Input variants
<input className={themeClasses.input.default} />

// Card variants
<div className={themeClasses.card.elevated}>
  Card Content
</div>
```

## 🔧 Configuration

### Theme Provider Props

```tsx
interface ThemeProviderProps {
  children: preact.ComponentChildren;
  defaultTheme?: 'light' | 'dark' | 'system';  // Default: 'system'
  storageKey?: string;                         // Default: 'theme'
  enableSystem?: boolean;                      // Default: true
}
```

### Dark Mode Toggle Variants

```tsx
// Switch variant (default)
<DarkModeToggle variant="switch" size="md" showLabel={true} />

// Button variant
<DarkModeToggle variant="button" size="lg" />

// Icon variant
<DarkModeToggle variant="icon" size="sm" />

// Dropdown variant
<DarkModeToggle variant="dropdown" />
```

## 🎯 Best Practices

### 1. Use Semantic Classes

```tsx
// Good: Semantic meaning
<div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
  
// Better: Use theme utilities
<div className={cn(themeClasses.bg.primary, themeClasses.text.primary)}>
```

### 2. Consistent Color Schemes

```tsx
// Use predefined trading colors
import { tradingColors } from '../lib/theme-config';

<span className={tradingColors.profit}>+5.2%</span>
<span className={tradingColors.loss}>-2.8%</span>
<span className={tradingColors.neutral}>0.0%</span>
```

### 3. Accessible Focus States

```tsx
// Use consistent focus rings
<button className={cn(
  'px-4 py-2 rounded-md',
  themeClasses.button.primary,
  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
)}>
```

### 4. Smooth Transitions

```tsx
// Add transitions for theme changes
<div className="transition-colors duration-200 bg-white dark:bg-gray-800">
```

## 📊 Trading-Specific Theming

### Signal Colors

```tsx
// BUY signal
<span className="text-green-600 dark:text-green-400">BUY</span>

// SELL signal
<span className="text-red-600 dark:text-red-400">SELL</span>

// HOLD signal
<span className="text-yellow-600 dark:text-yellow-400">HOLD</span>
```

### Chart Colors

```tsx
import { chartColors } from '../lib/theme-config';

const chartConfig = {
  colors: isDark ? chartColors.dark : chartColors.light,
  grid: {
    stroke: isDark ? chartColors.dark.grid : chartColors.light.grid,
  },
};
```

### Performance Indicators

```tsx
// Profit/Loss styling
<div className={cn(
  'px-3 py-1 rounded-full text-sm font-medium',
  pnl > 0 
    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
    : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
)}>
  {pnl > 0 ? '+' : ''}{pnl}%
</div>
```

## 🔄 Animation System

### Built-in Animations

```tsx
// Fade in/out
<div className="animate-fade-in">Content</div>

// Slide transitions
<div className="animate-slide-in">Content</div>

// Scale transitions
<div className="animate-scale-in">Content</div>

// Theme-aware glow effects
<div className="shadow-glow dark:shadow-glow-lg">Content</div>
```

### Custom Animations

```tsx
// Theme-aware pulse
<div className="animate-pulse bg-gray-200 dark:bg-gray-700">
  Loading...
</div>

// Gradient animations
<div className="animate-gradient-x bg-gradient-to-r from-blue-500 to-purple-600">
  Animated Background
</div>
```

## 🧪 Testing Dark Mode

### Manual Testing

1. **System Preference**: Change OS theme to test automatic detection
2. **Toggle Functionality**: Test all toggle variants
3. **Persistence**: Refresh page to verify theme persistence
4. **Multi-tab**: Open multiple tabs to test sync

### Automated Testing

```tsx
// Theme provider tests
import { render, screen } from '@testing-library/preact';
import { ThemeProvider } from '../contexts/ThemeContext';

test('applies dark theme correctly', () => {
  render(
    <ThemeProvider defaultTheme="dark">
      <div data-testid="content">Content</div>
    </ThemeProvider>
  );
  
  expect(document.documentElement).toHaveClass('dark');
});
```

## 🚨 Common Issues

### 1. Hydration Mismatch
```tsx
// Fix: Use mounted state
const [mounted, setMounted] = useState(false);
useEffect(() => setMounted(true), []);

if (!mounted) return null;
```

### 2. Theme Flash
```tsx
// Fix: Add theme detection script to HTML head
<script>
  (function() {
    const theme = localStorage.getItem('theme') || 'system';
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = theme === 'dark' || (theme === 'system' && systemDark);
    document.documentElement.classList.add(isDark ? 'dark' : 'light');
  })();
</script>
```

### 3. Chart Re-rendering
```tsx
// Fix: Memoize chart configurations
const chartConfig = useMemo(() => ({
  colors: isDark ? chartColors.dark : chartColors.light,
}), [isDark]);
```

## 📱 Mobile Considerations

### Touch Interactions

```tsx
// Larger touch targets for mobile
<DarkModeToggle 
  variant="switch" 
  size="lg" 
  className="md:size-md" 
/>
```

### PWA Theme Color

```tsx
// Update meta theme-color dynamically
useEffect(() => {
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute(
      'content',
      resolvedTheme === 'dark' ? '#1f2937' : '#ffffff'
    );
  }
}, [resolvedTheme]);
```

## 🔮 Future Enhancements

### Planned Features

1. **Theme Customization**: User-defined color schemes
2. **Accent Colors**: Multiple accent color options
3. **High Contrast Mode**: Accessibility enhancement
4. **Theme Scheduling**: Automatic theme switching by time
5. **Theme Presets**: Predefined theme combinations

### Advanced Usage

```tsx
// Theme customization hook
const useCustomTheme = () => {
  const [accentColor, setAccentColor] = useState('blue');
  const [contrast, setContrast] = useState('normal');
  
  const customTheme = useMemo(() => ({
    ...baseTheme,
    colors: {
      ...baseTheme.colors,
      primary: accentColor,
    },
  }), [accentColor]);
  
  return { customTheme, setAccentColor, setContrast };
};
```

## 📚 Resources

- [Tailwind CSS Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [System Color Schemes](https://web.dev/prefers-color-scheme/)
- [Accessibility Guidelines](https://webaim.org/articles/contrast/)
- [React Context Patterns](https://kentcdodds.com/blog/how-to-use-react-context-effectively)

## 🤝 Contributing

When adding new components:

1. **Use theme-aware classes**: Always support both light and dark themes
2. **Test thoroughly**: Verify appearance in both themes
3. **Document usage**: Add examples to component documentation
4. **Follow patterns**: Use established theme utilities and patterns

Example component template:

```tsx
import { cn, themeClasses } from '../lib/theme-config';

interface ComponentProps {
  variant?: 'primary' | 'secondary';
  className?: string;
}

export default function Component({ variant = 'primary', className }: ComponentProps) {
  return (
    <div className={cn(
      'transition-colors duration-200',
      themeClasses.bg.primary,
      themeClasses.text.primary,
      className
    )}>
      Content
    </div>
  );
}
```

This comprehensive dark mode system ensures consistent, accessible, and performant theming across the entire TradePulse.AI application. 