# 📁 TradePulse.AI - Public Assets

## Overview
Static assets served directly by the web server without build-time processing.

## Folder Structure

### `/icons/` - PWA & App Icons
- **favicon.ico, favicon.png, favicon.svg** - Browser favicons
- **icon-*.png** - PWA app icons for different sizes
- **shortcuts/** - PWA shortcut icons (future)

### `/images/` - Static Images
- **backgrounds/** - Hero sections, page backgrounds
- **logos/** - Brand logos, partner logos
- **screenshots/** - PWA app screenshots (future)

### Root Files
- **manifest.json** - PWA manifest configuration
- **sw.js** - Service worker for offline functionality

## Usage Guidelines

### Static Images
```html
<!-- Direct HTML reference -->
<img src="/images/logos/tradepulse-logo.svg" alt="TradePulse.AI" />

<!-- CSS background -->
.hero { background-image: url('/images/backgrounds/trading-hero.jpg'); }

<!-- Tailwind CSS -->
<div class="bg-[url('/images/backgrounds/market-pattern.png')]">
```

### PWA Configuration
- **manifest.json** - Defines app shortcuts to user dashboard pages
- **sw.js** - Handles offline caching and API requests
- **icons/** - Various sizes for different devices and contexts

## File Naming Convention
```
backgrounds/
├── hero-trading-main.jpg        # Main hero background
├── dashboard-pattern.png        # Dashboard subtle pattern
├── portfolio-gradient.svg       # Portfolio section gradient
└── market-data-abstract.jpg     # Market data visualization

logos/
├── tradepulse-logo.svg          # Main logo (scalable)
├── tradepulse-logo-dark.svg     # Dark theme variant
├── tradepulse-icon.png          # Square icon version
└── partner-logos/               # Third-party logos
```

## Performance Notes
- Images are served directly without optimization
- Use WebP format for better compression
- Keep file sizes reasonable for fast loading
- Consider lazy loading for below-the-fold images
