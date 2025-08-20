# 🖼️ TradePulse.AI - Frontend Images Structure

## 📁 Folder Organization

### `/public/images/` - Static Assets (Recommended for backgrounds)
Static images served directly by the web server without processing.

#### `/backgrounds/`
**Purpose**: Background images for components, sections, and pages
**Best for**: Large images, gradients, patterns, hero backgrounds
**Usage**: Referenced directly in CSS or component styles

```css
/* CSS usage */
.hero-section {
  background-image: url('/images/backgrounds/trading-hero.jpg');
}

/* Tailwind CSS usage */
<div className="bg-[url('/images/backgrounds/market-pattern.png')]">
```

#### `/icons/`
**Purpose**: Static icons, logos, favicons
**Best for**: SVG icons, PNG logos, favicon files
**Usage**: Direct HTML references

```astro
<!-- Astro component usage -->
<img src="/images/icons/logo.svg" alt="TradePulse.AI" />
```

#### `/charts/`
**Purpose**: Static chart images, screenshots, demo images
**Best for**: Marketing images, example charts, placeholder graphs
**Usage**: Direct references in components

```astro
<img src="/images/charts/performance-example.png" alt="Performance Chart" />
```

### `/src/assets/images/` - Processed Assets
Images that need build-time optimization or processing.

**Best for**: Images that need:
- Automatic optimization
- Multiple format generation (WebP, AVIF)
- Responsive image variants
- Import statements in components

```astro
---
import heroImage from '../assets/images/hero-background.jpg';
---

<img src={heroImage} alt="Hero" />
```

## 🎨 Background Image Best Practices

### 1. **File Naming Convention**
```
backgrounds/
├── hero-trading-dark.jpg          # Hero section, dark theme
├── hero-trading-light.jpg         # Hero section, light theme
├── dashboard-subtle-pattern.png   # Dashboard background pattern
├── portfolio-gradient.svg         # Portfolio section gradient
└── market-data-abstract.jpg       # Market data section background
```

### 2. **Recommended Formats & Sizes**
- **Hero backgrounds**: 1920x1080px (16:9), JPG/WebP
- **Section backgrounds**: 1200x600px, JPG/PNG/SVG
- **Patterns**: 400x400px (tileable), PNG/SVG
- **Gradients**: SVG (scalable) or CSS gradients

### 3. **Theme Support**
```
backgrounds/
├── dark-theme/
│   ├── hero-background-dark.jpg
│   ├── dashboard-pattern-dark.png
│   └── sidebar-gradient-dark.svg
└── light-theme/
    ├── hero-background-light.jpg
    ├── dashboard-pattern-light.png
    └── sidebar-gradient-light.svg
```

### 4. **Usage Examples**

#### CSS Variables (Recommended)
```css
:root {
  --bg-hero: url('/images/backgrounds/hero-trading-dark.jpg');
  --bg-dashboard: url('/images/backgrounds/dashboard-pattern.png');
}

[data-theme="light"] {
  --bg-hero: url('/images/backgrounds/hero-trading-light.jpg');
}

.hero {
  background-image: var(--bg-hero);
}
```

#### Tailwind CSS Classes
```astro
<!-- Static background -->
<section class="bg-[url('/images/backgrounds/market-data.jpg')] bg-cover bg-center">
  <h1>Market Data</h1>
</section>

<!-- Responsive background -->
<div class="bg-[url('/images/backgrounds/mobile-hero.jpg')] md:bg-[url('/images/backgrounds/desktop-hero.jpg')]">
  Content
</div>
```

#### Component with Props
```astro
---
// BackgroundSection.astro
export interface Props {
  backgroundImage?: string;
  className?: string;
}

const { backgroundImage, className = '' } = Astro.props;
const bgStyle = backgroundImage ? `background-image: url('${backgroundImage}')` : '';
---

<section class={`bg-cover bg-center ${className}`} style={bgStyle}>
  <slot />
</section>
```

## 🚀 Performance Tips

1. **Optimize image sizes** before adding to the project
2. **Use WebP format** for better compression
3. **Consider lazy loading** for below-the-fold backgrounds
4. **Use CSS gradients** instead of images when possible
5. **Preload critical backgrounds** in the `<head>`

```astro
---
// In page head
---
<link rel="preload" as="image" href="/images/backgrounds/hero-main.webp" />
```

## 📱 Trading-Specific Background Suggestions

### Hero Section
- Trading floor with charts
- Abstract financial data visualization  
- Cryptocurrency market patterns
- Professional trader workspace

### Dashboard
- Subtle grid patterns
- Low-opacity financial charts
- Geometric patterns suggesting data
- Minimal noise textures

### Portfolio Section
- Growth charts background
- Subtle candlestick patterns
- Profit/loss color gradients
- Investment-themed abstracts

### Analytics Section
- Data visualization backgrounds
- Statistical pattern overlays
- Performance chart silhouettes
- AI/ML themed graphics 