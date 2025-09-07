import { useState, useCallback } from 'preact/hooks';
import {
  X,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  TrendingUp,
  Bell,
  Volume2,
  VolumeX
} from 'lucide-preact';

export interface SignalNotificationData {
  signalId: string;
  symbol: string;
  action: 'buy' | 'sell';
  confidence: number;
  price: number;
}

export interface TradeNotificationData {
  tradeId: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  pnl?: number;
}

export type NotificationExtraData = SignalNotificationData | TradeNotificationData | Record<string, unknown>;

export interface NotificationData {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info' | 'signal' | 'trade';
  title: string;
  message: string;
  duration?: number; // in milliseconds, 0 for persistent
  action?: {
    label: string;
    onClick: () => void;
  };
  data?: NotificationExtraData;
  timestamp: Date;
}

interface NotificationSystemProps {
  maxNotifications?: number;
  defaultDuration?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  enableBrowserNotifications?: boolean;
  enableSound?: boolean;
}

let notificationId = 0;

// Global notification state
const notificationState = {
  notifications: [] as NotificationData[],
  listeners: [] as ((notifications: NotificationData[]) => void)[],
  
  addNotification: (notification: Omit<NotificationData, 'id' | 'timestamp'>) => {
    const newNotification: NotificationData = {
      ...notification,
      id: `notification-${++notificationId}`,
      timestamp: new Date()
    };
    
    notificationState.notifications.push(newNotification);
    notificationState.listeners.forEach(listener => listener([...notificationState.notifications]));
    
    return newNotification.id;
  },
  
  removeNotification: (id: string) => {
    notificationState.notifications = notificationState.notifications.filter(n => n.id !== id);
    notificationState.listeners.forEach(listener => listener([...notificationState.notifications]));
  },
  
  clearAll: () => {
    notificationState.notifications = [];
    notificationState.listeners.forEach(listener => listener([]));
  },
  
  subscribe: (listener: (notifications: NotificationData[]) => void) => {
    notificationState.listeners.push(listener);
    return () => {
      notificationState.listeners = notificationState.listeners.filter(l => l !== listener);
    };
  }
};

// Global notification functions
export const toast = {
  success: (title: string, message: string, options?: Partial<NotificationData>) => 
    notificationState.addNotification({ type: 'success', title, message, ...options }),
  
  warning: (title: string, message: string, options?: Partial<NotificationData>) => 
    notificationState.addNotification({ type: 'warning', title, message, ...options }),
  
  error: (title: string, message: string, options?: Partial<NotificationData>) => 
    notificationState.addNotification({ type: 'error', title, message, ...options }),
  
  info: (title: string, message: string, options?: Partial<NotificationData>) => 
    notificationState.addNotification({ type: 'info', title, message, ...options }),
  
  signal: (title: string, message: string, options?: Partial<NotificationData>) => 
    notificationState.addNotification({ type: 'signal', title, message, duration: 10000, ...options }),
  
  trade: (title: string, message: string, options?: Partial<NotificationData>) => 
    notificationState.addNotification({ type: 'trade', title, message, duration: 8000, ...options })
};

export function NotificationSystem({
  maxNotifications = 5,
  defaultDuration = 5000,
  position = 'top-right',
  enableBrowserNotifications = true,
  enableSound = true
}: NotificationSystemProps) {
  const [notifications, setNotifications] = useState<NotificationData[]>([]);
  const [browserPermission, setBrowserPermission] = useState<NotificationPermission>('default');
  const [soundEnabled, setSoundEnabled] = useState(enableSound);

  // Request browser notification permission
  const requestNotificationPermission = useCallback(async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      setBrowserPermission(permission);
      return permission === 'granted';
    }
    return false;
  }, []);

  // Play notification sound
  const playNotificationSound = useCallback((type: NotificationData['type']) => {
    if (!soundEnabled) return;
    
    try {
      // Create different tones for different notification types
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Set frequency based on notification type
      const frequencies = {
        success: 800,
        warning: 600,
        error: 400,
        info: 500,
        signal: 1000,
        trade: 900
      };
      
      oscillator.frequency.setValueAtTime(frequencies[type], audioContext.currentTime);
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
    } catch (err) {
      console.warn('Failed to play notification sound:', err);
    }
  }, [soundEnabled]);

  // Show browser notification
  const showBrowserNotification = useCallback((notification: NotificationData) => {
    if (!enableBrowserNotifications || browserPermission !== 'granted') return;
    
    const browserNotification = new Notification(notification.title, {
      body: notification.message,
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: notification.type,
      requireInteraction: notification.type === 'signal' || notification.type === 'trade',
      data: notification.data
    });
    
    browserNotification.onclick = () => {
      window.focus();
      if (notification.action) {
        notification.action.onClick();
      }
      browserNotification.close();
    };
    
    // Auto close after duration
    if (notification.duration && notification.duration > 0) {
      setTimeout(() => {
        browserNotification.close();
      }, notification.duration);
    }
  }, [enableBrowserNotifications, browserPermission]);

  // Handle new notifications
  const handleNewNotification = useCallback((newNotifications: NotificationData[]) => {
    const previousCount = notifications.length;
    const newCount = newNotifications.length;
    
    // If there are new notifications
    if (newCount > previousCount) {
      const latestNotification = newNotifications[newCount - 1];
      
      // Play sound
      playNotificationSound(latestNotification.type);
      
      // Show browser notification for important types
      if (['signal', 'trade', 'error'].includes(latestNotification.type)) {
        showBrowserNotification(latestNotification);
      }
    }
    
    // Limit number of notifications
    const limitedNotifications = newNotifications.slice(-maxNotifications);
    setNotifications(limitedNotifications);
    
    // Auto-remove notifications with duration
    limitedNotifications.forEach(notification => {
      if (notification.duration && notification.duration > 0) {
        setTimeout(() => {
          notificationState.removeNotification(notification.id);
        }, notification.duration);
      }
    });
  }, [notifications.length, maxNotifications, playNotificationSound, showBrowserNotification]);

  // Get notification icon
  const getNotificationIcon = (type: NotificationData['type']) => {
    const iconSize = 20;
    switch (type) {
      case 'success':
        return <CheckCircle size={iconSize} className="text-green-600" />;
      case 'warning':
        return <AlertTriangle size={iconSize} className="text-yellow-600" />;
      case 'error':
        return <XCircle size={iconSize} className="text-red-600" />;
      case 'info':
        return <Info size={iconSize} className="text-blue-600" />;
      case 'signal':
        return <TrendingUp size={iconSize} className="text-purple-600" />;
      case 'trade':
        return <TrendingDown size={iconSize} className="text-indigo-600" />;
      default:
        return <Info size={iconSize} className="text-gray-600" />;
    }
  };

  // Get notification colors
  const getNotificationColors = (type: NotificationData['type']) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-700';
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-700';
      case 'error':
        return 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-700';
      case 'info':
        return 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700';
      case 'signal':
        return 'bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-700';
      case 'trade':
        return 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-700';
      default:
        return 'bg-gray-50 dark:bg-gray-900/30 border-gray-200 dark:border-gray-700';
    }
  };

  // Get position classes
  const getPositionClasses = () => {
    switch (position) {
      case 'top-left':
        return 'top-4 left-4';
      case 'top-right':
        return 'top-4 right-4';
      case 'bottom-left':
        return 'bottom-4 left-4';
      case 'bottom-right':
        return 'bottom-4 right-4';
      default:
        return 'top-4 right-4';
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  };

  useEffect(() => {
    // Subscribe to notification updates
    const unsubscribe = notificationState.subscribe(handleNewNotification);
    
    // Set initial notifications
    setNotifications([...notificationState.notifications]);
    
    return unsubscribe;
  }, [handleNewNotification]);

  useEffect(() => {
    // Check browser notification permission on mount
    if ('Notification' in window) {
      setBrowserPermission(Notification.permission);
    }
  }, []);

  return (
    <>
      {/* Notification Container */}
      <div className={`fixed ${getPositionClasses()} z-50 max-w-sm w-full space-y-2`}>
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className={`
              border rounded-lg shadow-lg p-4 animate-in slide-in-from-right-full duration-300
              ${getNotificationColors(notification.type)}
            `}
          >
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                {getNotificationIcon(notification.type)}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                    {notification.title}
                  </h4>
                  <button
                    onClick={() => notificationState.removeNotification(notification.id)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <X size={16} />
                  </button>
                </div>
                
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                  {notification.message}
                </p>
                
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatTimeAgo(notification.timestamp)}
                  </span>
                  
                  {notification.action && (
                    <button
                      onClick={notification.action.onClick}
                      className="text-xs font-medium text-blue-600 hover:text-blue-800 
                                 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      {notification.action.label}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Notification Settings Floating Button */}
      <div className="fixed bottom-4 left-4 z-40">
        <div className="flex flex-col space-y-2">
          {/* Sound Toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-full shadow-lg transition-colors ${
              soundEnabled 
                ? 'bg-blue-600 text-white hover:bg-blue-700' 
                : 'bg-gray-300 text-gray-600 hover:bg-gray-400'
            }`}
            title={soundEnabled ? 'Disable Sound' : 'Enable Sound'}
          >
            {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>
          
          {/* Browser Notification Toggle */}
          {enableBrowserNotifications && (
            <button
              onClick={requestNotificationPermission}
              className={`p-2 rounded-full shadow-lg transition-colors ${
                browserPermission === 'granted'
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-yellow-600 text-white hover:bg-yellow-700'
              }`}
              title={
                browserPermission === 'granted' 
                  ? 'Browser Notifications Enabled' 
                  : 'Enable Browser Notifications'
              }
            >
              <Bell size={16} />
            </button>
          )}
        </div>
      </div>
    </>
  );
}

// Example usage component for testing
export function NotificationTester() {
  const testNotifications = () => {
    toast.success('Trade Executed', 'Successfully bought 0.1 BTC at $43,567');
    
    setTimeout(() => {
      toast.signal('AI Signal', 'Strong BUY signal detected for BTCUSDT', {
        action: {
          label: 'View Signal',
          onClick: () => console.log('Viewing signal...')
        }
      });
    }, 1000);
    
    setTimeout(() => {
      toast.warning('Risk Alert', 'Portfolio drawdown reached 5%');
    }, 2000);
    
    setTimeout(() => {
      toast.trade('Position Closed', 'BTCUSDT position closed with +$234 profit');
    }, 3000);
  };

  return (
    <div className="p-4">
      <button
        onClick={testNotifications}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        Test Notifications
      </button>
    </div>
  );
}

// Hook for using notifications in components
export function useNotifications() {
  const [notifications, setNotifications] = useState<NotificationData[]>([]);

  useEffect(() => {
    const unsubscribe = notificationState.subscribe(setNotifications);
    setNotifications([...notificationState.notifications]);
    return unsubscribe;
  }, []);

  return {
    notifications,
    toast,
    clearAll: notificationState.clearAll,
    removeNotification: notificationState.removeNotification
  };
} 