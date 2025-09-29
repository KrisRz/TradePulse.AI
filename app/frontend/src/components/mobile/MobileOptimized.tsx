/** @jsxImportSource preact */
import { useState, useRef, useEffect } from 'preact/hooks';
import type { ComponentChildren, FunctionalComponent } from 'preact';
import { ChevronDown, ChevronUp } from 'lucide-preact';

// Fallback icon type for lucide-preact compatibility
type IconComponent = FunctionalComponent<any>;

// X icon component (fallback if not available from lucide-preact)
const X: IconComponent = () => (
  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

// Mobile-optimized card component with touch interactions
interface MobileCardProps {
  children: ComponentChildren;
  className?: string;
  onTap?: () => void;
  onLongPress?: () => void;
  swipeActions?: {
    left?: { icon: IconComponent; label: string; action: () => void; color?: string };
    right?: { icon: IconComponent; label: string; action: () => void; color?: string };
  };
}

export function MobileCard({
  children,
  className = '',
  onTap,
  onLongPress,
  swipeActions
}: MobileCardProps) {
  const [isPressed, setIsPressed] = useState(false);
  const [swipeOffset, setSwipeOffset] = useState(0);
  const [showActions, setShowActions] = useState(false);
  const pressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cardRef = useRef<HTMLDivElement | null>(null);

  const handleTouchStart = (_e: TouchEvent) => {
    setIsPressed(true);
    
    if (onLongPress) {
      pressTimer.current = setTimeout(() => {
        onLongPress();
        setIsPressed(false);
      }, 500);
    }
  };

  const handleTouchEnd = () => {
    setIsPressed(false);
    
    if (pressTimer.current) {
      clearTimeout(pressTimer.current);
    }
    
    if (swipeOffset === 0 && onTap) {
      onTap();
    }
    
    // Reset swipe if not significant
    if (Math.abs(swipeOffset) < 100) {
      setSwipeOffset(0);
      setShowActions(false);
    }
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (pressTimer.current) {
      clearTimeout(pressTimer.current);
    }
    
    if (swipeActions && e.touches[0]) {
      // TODO: Implement swipe logic here
      // const startX = e.touches[0].clientX;
    }
  };

  return (
    <div
      ref={cardRef}
      className={`relative overflow-hidden transition-all duration-150 ${
        isPressed ? 'scale-98 bg-opacity-80' : ''
      } ${className}`}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onTouchMove={handleTouchMove}
      style={{ transform: `translateX(${swipeOffset}px)` }}
    >
      {children}
      
      {/* Swipe Actions */}
      {showActions && swipeActions && (
        <div className="absolute inset-y-0 right-0 flex items-center">
          {swipeActions.right && (
            <button
              onClick={swipeActions.right.action}
              className={`h-full px-4 flex items-center justify-center text-white ${
                swipeActions.right.color || 'bg-red-500'
              }`}
            >
              <swipeActions.right.icon className="w-5 h-5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// Mobile-optimized bottom sheet component
interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ComponentChildren;
  snapPoints?: number[];
  initialSnap?: number;
}

export function BottomSheet({
  isOpen,
  onClose,
  title,
  children,
  snapPoints = [0.3, 0.6, 0.9],
  initialSnap = 1
}: BottomSheetProps) {
  const [currentSnap] = useState(initialSnap);
  const [isDragging, setIsDragging] = useState(false);
  const sheetRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleDragStart = () => {
    setIsDragging(true);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />
      
      {/* Sheet */}
      <div
        ref={sheetRef}
        className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 rounded-t-2xl shadow-xl transition-transform duration-300 ease-out"
        style={{
          height: `${(snapPoints[currentSnap] ?? 0.5) * 100}vh`,
          transform: isDragging ? 'none' : 'translateY(0)'
        }}
      >
        {/* Handle */}
        <div
          className="flex justify-center pt-3 pb-2 cursor-pointer"
          onTouchStart={handleDragStart}
          onTouchEnd={handleDragEnd}
        >
          <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
        </div>
        
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {title}
            </h3>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {children}
        </div>
      </div>
    </>
  );
}

// Mobile-optimized expandable section
interface ExpandableSectionProps {
  title: string;
  children: ComponentChildren;
  defaultExpanded?: boolean;
  badge?: string | number;
}

export function ExpandableSection({
  title,
  children,
  defaultExpanded = false,
  badge
}: ExpandableSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <span className="font-medium text-gray-900 dark:text-white">
            {title}
          </span>
          {badge && (
            <span className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 text-xs font-medium px-2 py-1 rounded-full">
              {badge}
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        )}
      </button>
      
      {isExpanded && (
        <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          {children}
        </div>
      )}
    </div>
  );
}

// Mobile-optimized horizontal scroll container
interface HorizontalScrollProps {
  children: ComponentChildren;
  className?: string;
  showScrollIndicator?: boolean;
}

export function HorizontalScroll({
  children,
  className = '',
  showScrollIndicator = true
}: HorizontalScrollProps) {
  const [showLeftShadow, setShowLeftShadow] = useState(false);
  const [showRightShadow, setShowRightShadow] = useState(true);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
      setShowLeftShadow(scrollLeft > 0);
      setShowRightShadow(scrollLeft < scrollWidth - clientWidth - 1);
    }
  };

  useEffect(() => {
    handleScroll();
  }, [children]);

  return (
    <div className={`relative ${className}`}>
      {/* Left Shadow */}
      {showLeftShadow && (
        <div className="absolute left-0 top-0 bottom-0 w-4 bg-gradient-to-r from-white dark:from-gray-900 to-transparent z-10 pointer-events-none" />
      )}
      
      {/* Right Shadow */}
      {showRightShadow && (
        <div className="absolute right-0 top-0 bottom-0 w-4 bg-gradient-to-l from-white dark:from-gray-900 to-transparent z-10 pointer-events-none" />
      )}
      
      {/* Scroll Container */}
      <div
        ref={scrollRef}
        className="flex overflow-x-auto scrollbar-hide"
        onScroll={handleScroll}
        style={{
          scrollbarWidth: 'none',
          msOverflowStyle: 'none'
        }}
      >
        {children}
      </div>
      
      {/* Scroll Indicator */}
      {showScrollIndicator && (
        <div className="flex justify-center mt-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Swipe to see more →
          </div>
        </div>
      )}
    </div>
  );
}

// Mobile-optimized floating action button
interface FloatingActionButtonProps {
  icon: IconComponent;
  onClick: () => void;
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function FloatingActionButton({
  icon: Icon,
  onClick,
  position = 'bottom-right',
  className = '',
  size = 'md'
}: FloatingActionButtonProps) {
  const positionClasses = {
    'bottom-right': 'bottom-20 right-4 lg:bottom-4',
    'bottom-left': 'bottom-20 left-4 lg:bottom-4',
    'top-right': 'top-20 right-4',
    'top-left': 'top-20 left-4'
  };

  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-14 h-14',
    lg: 'w-16 h-16'
  };

  const iconSizes = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-7 h-7'
  };

  return (
    <button
      onClick={onClick}
      className={`fixed ${positionClasses[position]} ${sizeClasses[size]} bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center z-30 ${className}`}
    >
      <Icon className={iconSizes[size]} />
    </button>
  );
}

// Mobile-optimized pull-to-refresh component
interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: ComponentChildren;
  threshold?: number;
}

export function PullToRefresh({
  onRefresh,
  children,
  threshold = 100
}: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [canRefresh, setCanRefresh] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  let startY = 0;

  const handleTouchStart = (e: TouchEvent) => {
    if (window.scrollY === 0 && e.touches[0]) {
      startY = e.touches[0].clientY;
    }
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (window.scrollY === 0 && !isRefreshing && e.touches[0]) {
      const currentY = e.touches[0].clientY;
      const diff = currentY - startY;
      
      if (diff > 0) {
        e.preventDefault();
        const distance = Math.min(diff * 0.5, threshold * 1.5);
        setPullDistance(distance);
        setCanRefresh(distance >= threshold);
      }
    }
  };

  const handleTouchEnd = async () => {
    if (canRefresh && !isRefreshing) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
        setPullDistance(0);
        setCanRefresh(false);
      }
    } else {
      setPullDistance(0);
      setCanRefresh(false);
    }
  };

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('touchstart', handleTouchStart);
      container.addEventListener('touchmove', handleTouchMove, { passive: false });
      container.addEventListener('touchend', handleTouchEnd);
      
      return () => {
        container.removeEventListener('touchstart', handleTouchStart);
        container.removeEventListener('touchmove', handleTouchMove);
        container.removeEventListener('touchend', handleTouchEnd);
      };
    }
    return undefined;
  }, [canRefresh, isRefreshing]);

  return (
    <div ref={containerRef} className="relative">
      {/* Pull indicator */}
      {pullDistance > 0 && (
        <div
          className="absolute top-0 left-0 right-0 flex items-center justify-center bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 transition-all duration-200"
          style={{
            height: `${pullDistance}px`,
            transform: `translateY(-${pullDistance}px)`
          }}
        >
          <div className="flex flex-col items-center">
            <div
              className={`w-6 h-6 border-2 border-current rounded-full transition-transform duration-200 ${
                isRefreshing ? 'animate-spin' : canRefresh ? 'rotate-180' : ''
              }`}
              style={{
                borderTopColor: 'transparent'
              }}
            />
            <span className="text-xs mt-1">
              {isRefreshing ? 'Refreshing...' : canRefresh ? 'Release to refresh' : 'Pull to refresh'}
            </span>
          </div>
        </div>
      )}
      
      <div
        className="transition-transform duration-200"
        style={{
          transform: `translateY(${pullDistance}px)`
        }}
      >
        {children}
      </div>
    </div>
  );
}

// Mobile-optimized toast notification
interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  isVisible: boolean;
  onClose: () => void;
  duration?: number;
}

export function Toast({
  message,
  type = 'info',
  isVisible,
  onClose,
  duration = 3000
}: ToastProps) {
  useEffect(() => {
    if (!isVisible || duration <= 0) return undefined;
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [isVisible, duration, onClose]);

  const typeClasses = {
    success: 'bg-green-500 text-white',
    error: 'bg-red-500 text-white',
    warning: 'bg-yellow-500 text-white',
    info: 'bg-blue-500 text-white'
  };

  if (!isVisible) return null;

  return (
    <div className="fixed top-4 left-4 right-4 z-50 lg:left-auto lg:right-4 lg:w-80">
      <div
        className={`${typeClasses[type]} rounded-lg shadow-lg p-4 flex items-center justify-between animate-slide-down`}
      >
        <span className="text-sm font-medium flex-1">{message}</span>
        <button
          onClick={onClose}
          className="ml-3 text-white hover:text-gray-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// Utility hook for mobile detection
export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  return isMobile;
}

// Utility hook for touch device detection
export function useIsTouchDevice() {
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  useEffect(() => {
    setIsTouchDevice('ontouchstart' in window || navigator.maxTouchPoints > 0);
  }, []);

  return isTouchDevice;
} 