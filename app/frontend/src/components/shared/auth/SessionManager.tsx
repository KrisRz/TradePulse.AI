import { useEffect, useState } from 'preact/hooks';
import { useAuth } from '../../contexts/AuthContext';
import { getTokenInfo, shouldRefreshToken } from '../../lib/jwt-manager';

interface SessionManagerProps {
  children: preact.ComponentChildren;
  idleTimeout?: number; // in milliseconds
  warningTime?: number; // in milliseconds
  onSessionExpired?: () => void;
}

export default function SessionManager({
  children,
  idleTimeout = 30 * 60 * 1000, // 30 minutes default
  warningTime = 5 * 60 * 1000, // 5 minutes warning
  onSessionExpired
}: SessionManagerProps) {
  const [isClient, setIsClient] = useState(false);
  const [showWarning, setShowWarning] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);

  // Handle client-side hydration
  useEffect(() => {
    setIsClient(true);
  }, []);

  // During SSR, just render children
  if (!isClient) {
    return <>{children}</>;
  }

  // Now we're on the client side, safe to use useAuth
  let authContext;
  try {
    authContext = useAuth();
  } catch (error) {
    // If useAuth fails (no AuthProvider), render children without session management
    console.warn('SessionManager: AuthProvider not found, rendering children without session management');
    return <>{children}</>;
  }
  
  const { isAuthenticated, token, logout } = authContext;

  useEffect(() => {
    if (!isAuthenticated || !token) return;

    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    let warningTimer: ReturnType<typeof setTimeout> | null = null;
    let countdownTimer: ReturnType<typeof setTimeout> | null = null;

    const resetTimers = () => {
      // Clear existing timers
      if (idleTimer) clearTimeout(idleTimer);
      if (warningTimer) clearTimeout(warningTimer);
      if (countdownTimer) clearInterval(countdownTimer);

      setShowWarning(false);

      // Check if token needs refresh
      if (shouldRefreshToken(token)) {
        // Token refresh will be handled by AuthContext
        return;
      }

      // Set warning timer
      warningTimer = setTimeout(() => {
        setShowWarning(true);
        setTimeLeft(warningTime);

        // Start countdown
        countdownTimer = setInterval(() => {
          setTimeLeft(prev => {
            if (prev <= 1000) {
              handleSessionExpired();
              return 0;
            }
            return prev - 1000;
          });
        }, 1000);
      }, idleTimeout - warningTime);

      // Set idle timer
      idleTimer = setTimeout(() => {
        handleSessionExpired();
      }, idleTimeout);
    };

    const handleSessionExpired = async () => {
      setShowWarning(false);
      onSessionExpired?.();
      await logout();
    };

    const handleActivity = () => {
      if (isAuthenticated) {
        resetTimers();
      }
    };

    // Activity events to track
    const events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
    ];

    // Add event listeners
    events.forEach(event => {
      document.addEventListener(event, handleActivity, true);
    });

    // Initial timer setup
    resetTimers();

    // Token expiry check
    const tokenInfo = getTokenInfo(token);
    if (!tokenInfo.isValid) {
      handleSessionExpired();
      return;
    }

    // Cleanup
    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleActivity, true);
      });
      if (idleTimer) clearTimeout(idleTimer);
      if (warningTimer) clearTimeout(warningTimer);
      if (countdownTimer) clearInterval(countdownTimer);
    };
  }, [isAuthenticated, token, idleTimeout, warningTime, logout, onSessionExpired]);

  const handleExtendSession = () => {
    setShowWarning(false);
  };

  const handleLogoutNow = async () => {
    setShowWarning(false);
    await logout();
  };

  const formatTime = (ms: number): string => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <>
      {children}
      
      {/* Session Warning Modal */}
      {showWarning && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="session-warning-title" role="dialog" aria-modal="true">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>

            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <div className="sm:flex sm:items-start">
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 dark:bg-yellow-900 sm:mx-0 sm:h-10 sm:w-10">
                  <svg className="h-6 w-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white" id="session-warning-title">
                    Session Expiring Soon
                  </h3>
                  <div className="mt-2">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Your session will expire in <strong className="text-yellow-600 dark:text-yellow-400">{formatTime(timeLeft)}</strong> due to inactivity.
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                      Click "Stay Logged In" to extend your session or "Logout" to end it now.
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleExtendSession}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Stay Logged In
                </button>
                <button
                  type="button"
                  onClick={handleLogoutNow}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:w-auto sm:text-sm"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
} 