import { useEffect } from 'preact/hooks';
import { ThemeProvider } from '../../contexts/ThemeContext';
import { AuthProvider } from '../../contexts/AuthContext';
import SessionManager from '../auth/SessionManager';
import DarkModeToggle from '../ui/DarkModeToggle';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { cn } from '../../lib/theme-config';

interface AppLayoutProps {
  children: preact.ComponentChildren;
}

// Layout content that depends on theme and auth context
function AppLayoutContent({ children }: AppLayoutProps) {
  const { resolvedTheme } = useTheme();
  const { isAuthenticated, user } = useAuth();

  // Apply theme to document body
  useEffect(() => {
    document.body.className = cn(
      'min-h-screen transition-colors duration-200',
      resolvedTheme === 'dark' 
        ? 'bg-gray-900 text-white' 
        : 'bg-gray-50 text-gray-900'
    );
  }, [resolvedTheme]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Theme-aware navigation */}
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">TP</span>
                </div>
              </div>
              <div className="ml-4">
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  TradePulse.AI
                </h1>
              </div>
            </div>

            {/* Navigation items */}
            <div className="flex items-center space-x-4">
              {isAuthenticated && (
                <>
                  {/* User info */}
                  <div className="flex items-center space-x-3">
                    <div className="text-sm">
                      <span className="text-gray-500 dark:text-gray-400">Welcome,</span>
                      <span className="ml-1 font-medium text-gray-900 dark:text-white">
                        {user?.email}
                      </span>
                    </div>
                    
                    {/* Role badge */}
                    <span className={cn(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      user?.role === 'admin' 
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300'
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300'
                    )}>
                      {user?.role}
                    </span>
                  </div>
                </>
              )}

              {/* Dark mode toggle */}
              <DarkModeToggle variant="icon" size="md" />
            </div>
          </div>
        </div>
      </nav>

      {/* Main content area */}
      <main className="flex-1 bg-gray-50 dark:bg-gray-900">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              © 2024 TradePulse.AI. All rights reserved.
            </p>
            <div className="flex items-center space-x-4">
              <a 
                href="#" 
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              >
                Privacy Policy
              </a>
              <a 
                href="#" 
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              >
                Terms of Service
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Main layout component with providers
export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <ThemeProvider defaultTheme="system" enableSystem={true}>
      <AuthProvider>
        <SessionManager>
          <AppLayoutContent>
            {children}
          </AppLayoutContent>
        </SessionManager>
      </AuthProvider>
    </ThemeProvider>
  );
} 