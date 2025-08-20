export interface User {
  id: string;
  email: string;
  username: string;
  role: 'user' | 'admin';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  preferences?: UserPreferences;
  subscription?: UserSubscription;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    email: boolean;
    push: boolean;
    discord: boolean;
    telegram: boolean;
  };
  trading: {
    default_position_size: number;
    risk_tolerance: 'low' | 'medium' | 'high';
    auto_trading_enabled: boolean;
  };
}

export interface UserSubscription {
  plan: 'free' | 'premium' | 'pro';
  status: 'active' | 'cancelled' | 'expired';
  started_at: string;
  expires_at?: string;
  features: string[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  expires_in: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface AuthError {
  detail: string;
  code?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
} 