/**
 * Components Barrel Export
 * CRYSTAL CLEAR COMPONENT STRUCTURE
 */

// 👨‍💼 ADMIN COMPONENTS (Full System Access)
export * from './admin';

// 👤 USER COMPONENTS (Limited Permissions: user_dashboard, portfolio_view, trading_signals, basic_analytics)
export * from './user';

// 🤝 SHARED COMPONENTS (Used by Both Admin & User)
export * from './shared';

// 🎨 ASTRO COMPONENTS (Static Site Components)
export * from './astro';