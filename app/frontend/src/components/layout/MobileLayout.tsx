import { useState } from 'preact/hooks';
import { ComponentChildren } from 'preact';
import {
  Menu,
  X,
  Home,
  TrendingUp,
  BarChart3,
  Settings,
  Bell,
  User,
  LogOut,
  ChevronRight,
  ArrowLeft,
  Search,
  Plus,
  DollarSign,
  Activity
} from 'lucide-preact';
import type { Icon } from 'lucide-preact';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import DarkModeToggle from '../ui/DarkModeToggle';

interface HeaderAction {
  icon: Icon;
  label: string;
  onClick: () => void;
  color?: string;
}

interface MobileLayoutProps {
  children: ComponentChildren;
  title?: string;
  showBackButton?: boolean;
  showSearch?: boolean;
  onBack?: () => void;
  onSearch?: (query: string) => void;
  headerActions?: HeaderAction[];
}

export default function MobileLayout({
  children,
  title = 'TradePulse.AI',
  showBackButton = false,
  showSearch = false,
  onBack,
  onSearch,
  headerActions = []
}: MobileLayoutProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [notifications, setNotifications] = useState(0);
  const { user, logout } = useAuth();
  const { theme } = useTheme();

  // Close menu when route changes
  useEffect(() => {
    setIsMenuOpen(false);
    setIsSearchOpen(false);
  }, [title]);

  // Handle swipe gestures for menu
  useEffect(() => {
    let startX = 0;
    let startY = 0;
    
    const handleTouchStart = (e: TouchEvent) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    };
    
    const handleTouchEnd = (e: TouchEvent) => {
      const endX = e.changedTouches[0].clientX;
      const endY = e.changedTouches[0].clientY;
      const diffX = endX - startX;
      const diffY = endY - startY;
      
      // Horizontal swipe from left edge to open menu
      if (Math.abs(diffX) > Math.abs(diffY) && diffX > 50 && startX < 50) {
        setIsMenuOpen(true);
      }
      
      // Horizontal swipe to close menu
      if (Math.abs(diffX) > Math.abs(diffY) && diffX < -50 && isMenuOpen) {
        setIsMenuOpen(false);
      }
    };
    
    document.addEventListener('touchstart', handleTouchStart);
    document.addEventListener('touchend', handleTouchEnd);
    
    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [isMenuOpen]);

  const navigationItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: Home,
      badge: null
    },
    {
      name: 'Signals',
      href: '/dashboard/signals',
      icon: TrendingUp,
      badge: notifications > 0 ? notifications : null
    },
    {
      name: 'Trading',
      href: '/dashboard/trading',
      icon: DollarSign,
      badge: null
    },
    {
      name: 'Analytics',
      href: '/dashboard/analytics',
      icon: BarChart3,
      badge: null
    }
  ];

  const handleSearch = (e: Event) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch?.(searchQuery);
      setIsSearchOpen(false);
      setSearchQuery('');
    }
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      logout();
      window.location.href = '/';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 relative">
      {/* Mobile Header */}
      <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex items-center justify-between px-4 py-3">
          {/* Left Section */}
          <div className="flex items-center space-x-3">
            {showBackButton ? (
              <button
                onClick={onBack || (() => window.history.back())}
                className="p-2 -ml-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                aria-label="Go back"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={() => setIsMenuOpen(true)}
                className="p-2 -ml-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors lg:hidden"
                aria-label="Open menu"
              >
                <Menu className="w-6 h-6" />
              </button>
            )}
            
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {title}
            </h1>
          </div>
          
          {/* Right Section */}
          <div className="flex items-center space-x-2">
            {/* Search Button */}
            {showSearch && (
              <button
                onClick={() => setIsSearchOpen(true)}
                className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                aria-label="Search"
              >
                <Search className="w-5 h-5" />
              </button>
            )}
            
            {/* Custom Header Actions */}
            {headerActions.map((action, index) => (
              <button
                key={index}
                onClick={action.onClick}
                className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                aria-label={action.label}
              >
                {action.icon}
              </button>
            ))}
            
            {/* Notifications */}
            <button
              className="relative p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              aria-label="Notifications"
            >
              <Bell className="w-5 h-5" />
              {notifications > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {notifications > 9 ? '9+' : notifications}
                </span>
              )}
            </button>
          </div>
        </div>
        
        {/* Search Bar (when open) */}
        {isSearchOpen && (
          <div className="px-4 pb-3">
            <form onSubmit={handleSearch} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.currentTarget.value)}
                placeholder="Search signals, symbols, trades..."
                className="w-full px-3 py-2 pl-10 pr-20 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                autoFocus
              />
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <button
                type="button"
                onClick={() => setIsSearchOpen(false)}
                className="absolute right-2 top-2 px-2 py-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              >
                Cancel
              </button>
            </form>
          </div>
        )}
      </header>

      {/* Mobile Slide-out Menu */}
      {isMenuOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-50 bg-black bg-opacity-50 lg:hidden"
            onClick={() => setIsMenuOpen(false)}
          />
          
          {/* Menu Panel */}
          <div className="fixed top-0 left-0 z-50 w-80 max-w-[80vw] h-full bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 ease-in-out lg:hidden">
            {/* Menu Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">TP</span>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    TradePulse.AI
                  </h2>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    AI Trading Platform
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsMenuOpen(false)}
                className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* User Info */}
            {user && (
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {user.email}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {user.role === 'admin' ? 'Administrator' : 'Trader'}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Navigation */}
            <nav className="flex-1 py-4">
              {navigationItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = window.location.pathname === item.href;
                
                return (
                  <a
                    key={item.name}
                    href={item.href}
                    className={`flex items-center justify-between px-4 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-r-2 border-blue-600'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <div className="flex items-center space-x-3">
                      <IconComponent className="w-5 h-5" />
                      <span>{item.name}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {item.badge && (
                        <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                          {item.badge}
                        </span>
                      )}
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </a>
                );
              })}
            </nav>
            
            {/* Menu Footer */}
            <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-3">
              {/* Theme Toggle */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Dark Mode
                </span>
                <DarkModeToggle variant="switch" size="sm" />
              </div>
              
              {/* Settings */}
              <button className="flex items-center justify-between w-full px-0 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors">
                <div className="flex items-center space-x-3">
                  <Settings className="w-5 h-5" />
                  <span>Settings</span>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </button>
              
              {/* Logout */}
              <button
                onClick={handleLogout}
                className="flex items-center space-x-3 w-full px-0 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* Main Content */}
      <main className="pb-20 lg:pb-0">
        {children}
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 lg:hidden">
        <div className="flex items-center justify-around">
          {navigationItems.map((item) => {
            const IconComponent = item.icon;
            const isActive = window.location.pathname === item.href;
            
            return (
              <a
                key={item.name}
                href={item.href}
                className={`flex flex-col items-center py-2 px-3 transition-colors relative ${
                  isActive
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <div className="relative">
                  <IconComponent className="w-5 h-5" />
                  {item.badge && (
                    <span className="absolute -top-2 -right-2 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                      {item.badge > 9 ? '9+' : item.badge}
                    </span>
                  )}
                </div>
                <span className="text-xs mt-1 text-center">
                  {item.name}
                </span>
                {isActive && (
                  <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-6 h-0.5 bg-blue-600 dark:bg-blue-400 rounded-full" />
                )}
              </a>
            );
          })}
        </div>
      </nav>

      {/* PWA Install Prompt */}
      <PWAInstallPrompt />
    </div>
  );
}

// PWA Install Prompt Component
function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowPrompt(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstall = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        console.log('PWA installation accepted');
      }
      
      setDeferredPrompt(null);
      setShowPrompt(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    localStorage.setItem('pwa-prompt-dismissed', 'true');
  };

  // Don't show if already dismissed
  if (localStorage.getItem('pwa-prompt-dismissed')) {
    return null;
  }

  if (!showPrompt) {
    return null;
  }

  return (
    <div className="fixed bottom-20 left-4 right-4 z-40 bg-blue-600 text-white rounded-lg shadow-lg p-4 lg:bottom-4 lg:left-auto lg:right-4 lg:w-80">
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 bg-white bg-opacity-20 rounded-lg flex items-center justify-center flex-shrink-0">
          <Plus className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium">Install TradePulse.AI</h4>
          <p className="text-xs text-blue-100 mt-1">
            Add to your home screen for quick access to your trading dashboard.
          </p>
        </div>
      </div>
      <div className="flex space-x-3 mt-3">
        <button
          onClick={handleInstall}
          className="flex-1 bg-white text-blue-600 text-sm font-medium py-2 px-3 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Install
        </button>
        <button
          onClick={handleDismiss}
          className="text-blue-100 text-sm font-medium py-2 px-3 hover:text-white transition-colors"
        >
          Not now
        </button>
      </div>
    </div>
  );
} 