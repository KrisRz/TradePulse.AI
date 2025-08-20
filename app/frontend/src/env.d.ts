/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

// Preact module declarations
declare module 'preact/hooks' {
  export function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void];
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useMemo<T>(factory: () => T, deps: any[]): T;
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T;
  export function useRef<T>(initialValue: T): { current: T };
}

declare module 'lucide-preact' {
  export const MessageSquare: any;
  export const Send: any;
  export const Users: any;
  export const Bell: any;
  export const Settings: any;
  export const Eye: any;
  export const EyeOff: any;
  export const Edit: any;
  export const Trash2: any;
  export const Plus: any;
  export const Filter: any;
  export const Calendar: any;
  export const Clock: any;
  export const CheckCircle: any;
  export const XCircle: any;
  export const AlertTriangle: any;
  export const Mail: any;
  export const Smartphone: any;
  export const Monitor: any;
  export const Globe: any;
  export const TrendingUp: any;
  export const BarChart3: any;
  export const FileText: any;
  export const Download: any;
  export const RefreshCw: any;
  export const Star: any;
  export const Copy: any;
  export const ExternalLink: any;
  export const Zap: any;
  export const Database: any;
  export const Server: any;
  export const Activity: any;
  export const Wallet: any;
  export const ArrowDownLeft: any;
  export const ArrowUpRight: any;
  export const Shield: any;
  export const MoreVertical: any;
  export const Ban: any;
  export const TrendingDown: any;
  export const UserPlus: any;
  export const UserCheck: any;
  export const UserX: any;
  export const Key: any;
  export const ChevronDown: any;
  export const ChevronUp: any;
  export const DollarSign: any;
  export const Search: any;
  
  // Fix: Add missing icons
  export const Brain: any;
  export const Target: any;
  export const ArrowRight: any;
}