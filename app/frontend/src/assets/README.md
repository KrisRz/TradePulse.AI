# 📁 TradePulse.AI - Source Assets

## Overview
Assets that undergo build-time processing and optimization by Astro/Vite.

## Folder Structure

### `/images/` - Processed Images
- **components/** - Component-specific images
- **backgrounds/** - Optimized background images
- **charts/** - Chart templates and examples

### `/icons/` - SVG Icons
- Component icons that need build-time optimization
- Icons imported directly into components

### `/fonts/` - Custom Fonts
- Web fonts that need optimization
- Font files processed by the build system

## Usage Guidelines

### Import in Components
```astro
---
// Astro component
import heroImage from '../assets/images/backgrounds/hero-main.jpg';
import chartIcon from '../assets/icons/chart.svg';
---

<img src={heroImage} alt="Hero Background" />
<img src={chartIcon} alt="Chart" />
```

```tsx
// React/Preact component
import portfolioChart from '../assets/images/components/portfolio-example.png';

export default function Portfolio() {
  return <img src={portfolioChart} alt="Portfolio Chart" />;
}
```

### Build-Time Benefits
- **Automatic optimization** - Images compressed and resized
- **Format conversion** - WebP/AVIF generation
- **Cache busting** - Automatic filename hashing
- **Import validation** - Build fails if assets missing

## File Organization

### Component-Specific Images
```
images/components/
├── admin/
│   ├── dashboard-preview.png
│   ├── system-status-chart.png
│   └── user-management-table.png
├── user/
│   ├── portfolio-overview.png
│   ├── signals-interface.png
│   └── analytics-charts.png
└── shared/
    ├── loading-spinner.svg
    ├── error-illustration.svg
    └── success-checkmark.svg
```

### Background Images
```
images/backgrounds/
├── hero-gradient.svg           # Scalable gradient
├── dashboard-texture.png       # Subtle texture
├── portfolio-pattern.svg       # Repeatable pattern
└── analytics-abstract.jpg     # Data visualization theme
```

### Icons
```
icons/
├── ui/
│   ├── arrow-up.svg
│   ├── arrow-down.svg
│   └── refresh.svg
├── trading/
│   ├── buy-signal.svg
│   ├── sell-signal.svg
│   └── portfolio.svg
└── admin/
    ├── system-control.svg
    ├── user-management.svg
    └── analytics.svg
```

## Best Practices
1. **Use appropriate formats**: SVG for icons, JPG for photos, PNG for graphics
2. **Optimize before adding**: Compress images before committing
3. **Consistent naming**: Use kebab-case and descriptive names
4. **Group by usage**: Organize by component or feature area
5. **Import validation**: Always test imports in components
