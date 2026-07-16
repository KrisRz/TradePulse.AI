import { getSecurityConfig } from '@/config/environments';

// Unified token storage key ('token') - single source of truth in config/environments.ts
const getTokenKey = () => getSecurityConfig().tokenStorageKey;

export const jwtManager = {
  getToken: () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(getTokenKey());
    }
    return null;
  },

  setToken: (token: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(getTokenKey(), token);
    }
  },

  removeToken: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(getTokenKey());
    }
  },
  
  isTokenValid: (token: string | null): boolean => {
    if (!token) return false;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp > Date.now() / 1000;
    } catch {
      return false;
    }
  }
};

export const getTokenInfo = (token: string | null) => {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload;
  } catch {
    return null;
  }
};

export const shouldRefreshToken = (token: string | null): boolean => {
  const info = getTokenInfo(token);
  if (!info) return false;
  const expTime = info.exp * 1000;
  const currentTime = Date.now();
  const timeUntilExpiry = expTime - currentTime;
  return timeUntilExpiry < 5 * 60 * 1000; // Refresh if less than 5 minutes left
};
