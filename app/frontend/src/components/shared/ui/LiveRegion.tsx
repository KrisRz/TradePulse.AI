import { useEffect, useRef } from 'preact/hooks';
import type { ComponentChildren } from 'preact';

interface LiveRegionProps {
  /** Content to announce to screen readers */
  children: ComponentChildren;
  /** Politeness level for announcements */
  politeness?: 'polite' | 'assertive' | 'off';
  /** Atomic updates - announce entire content vs incremental */
  atomic?: boolean;
  /** Relevant updates to announce */
  relevant?: 'additions' | 'removals' | 'text' | 'all';
  /** Visual styling (usually hidden) */
  className?: string;
  /** Debounce announcements to prevent spam */
  debounceMs?: number;
}

/**
 * LiveRegion Component
 * 
 * WCAG 2.1 AA compliant live region for real-time announcements:
 * - Announces price changes to screen readers
 * - Debounces rapid updates to prevent spam
 * - Configurable politeness levels
 * - Critical for trading platform accessibility
 * 
 * Usage:
 * - Price updates: politeness="polite" 
 * - Alerts/Errors: politeness="assertive"
 * - P&L changes: politeness="polite" with atomic=true
 */
export function LiveRegion({
  children,
  politeness = 'polite',
  atomic = false,
  relevant = 'text',
  className = 'sr-only',
  debounceMs = 1000
}: LiveRegionProps) {
  const announceRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastAnnouncementRef = useRef<string>('');

  useEffect(() => {
    if (!announceRef.current || !children) return;

    const newContent = typeof children === 'string' ? children : announceRef.current.textContent || '';
    
    // Avoid duplicate announcements
    if (newContent === lastAnnouncementRef.current) return;
    
    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Debounce announcements
    timeoutRef.current = setTimeout(() => {
      if (announceRef.current) {
        lastAnnouncementRef.current = newContent;
        // Force re-announcement by clearing and setting content
        announceRef.current.textContent = '';
        setTimeout(() => {
          if (announceRef.current) {
            announceRef.current.textContent = newContent;
          }
        }, 10);
      }
    }, debounceMs);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [children, debounceMs]);

  return (
    <div
      ref={announceRef}
      aria-live={politeness}
      aria-atomic={atomic}
      aria-relevant={relevant}
      className={className}
      role="status"
    >
      {children}
    </div>
  );
}

/**
 * PriceAnnouncer Component
 * 
 * Specialized live region for price updates
 */
interface PriceAnnouncerProps {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  formatPrice?: (price: number) => string;
}

export function PriceAnnouncer({
  symbol,
  price,
  change,
  changePercent,
  formatPrice = (p) => p.toFixed(2)
}: PriceAnnouncerProps) {
  const direction = change >= 0 ? 'up' : 'down';
  const changeText = change >= 0 ? 'increased' : 'decreased';
  
  const announcement = `${symbol} price ${changeText} to ${formatPrice(price)}, ${direction} ${Math.abs(changePercent).toFixed(2)} percent`;

  return (
    <LiveRegion politeness="polite" debounceMs={2000}>
      {announcement}
    </LiveRegion>
  );
}

/**
 * AlertAnnouncer Component
 * 
 * Specialized live region for critical alerts
 */
interface AlertAnnouncerProps {
  type: 'success' | 'warning' | 'error' | 'info';
  message: string;
  details?: string;
}

export function AlertAnnouncer({
  type,
  message,
  details
}: AlertAnnouncerProps) {
  const announcement = `${type.toUpperCase()}: ${message}${details ? `. ${details}` : ''}`;

  return (
    <LiveRegion 
      politeness={type === 'error' ? 'assertive' : 'polite'} 
      atomic={true}
      debounceMs={500}
    >
      {announcement}
    </LiveRegion>
  );
}

/**
 * TradingStatusAnnouncer Component
 * 
 * Specialized live region for trading status updates
 */
interface TradingStatusAnnouncerProps {
  status: 'connected' | 'disconnected' | 'error' | 'maintenance';
  details?: string;
}

export function TradingStatusAnnouncer({
  status,
  details
}: TradingStatusAnnouncerProps) {
  const statusMessages = {
    connected: 'Trading system connected and operational',
    disconnected: 'Trading system disconnected',
    error: 'Trading system error detected',
    maintenance: 'Trading system under maintenance'
  };

  const announcement = `${statusMessages[status]}${details ? `. ${details}` : ''}`;

  return (
    <LiveRegion 
      politeness={status === 'error' ? 'assertive' : 'polite'}
      atomic={true}
      debounceMs={3000}
    >
      {announcement}
    </LiveRegion>
  );
}

/**
 * PositionAnnouncer Component
 * 
 * Specialized live region for position updates
 */
interface PositionAnnouncerProps {
  action: 'opened' | 'closed' | 'updated';
  symbol: string;
  side: 'long' | 'short';
  size?: number;
  pnl?: number;
  formatCurrency?: (amount: number) => string;
}

export function PositionAnnouncer({
  action,
  symbol,
  side,
  size,
  pnl,
  formatCurrency = (amount) => `$${amount.toFixed(2)}`
}: PositionAnnouncerProps) {
  let announcement = `Position ${action}: ${side} ${symbol}`;
  
  if (size) {
    announcement += ` size ${size}`;
  }
  
  if (pnl !== undefined) {
    const pnlText = pnl >= 0 ? 'profit' : 'loss';
    announcement += `, ${pnlText} ${formatCurrency(Math.abs(pnl))}`;
  }

  return (
    <LiveRegion 
      politeness="polite"
      atomic={true}
      debounceMs={1500}
    >
      {announcement}
    </LiveRegion>
  );
} 