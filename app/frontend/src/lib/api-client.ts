/**
 * Professional API Client for TradePulse.AI
 * 
 * Features:
 * - Environment-aware (local dev vs AWS production)
 * - Automatic authentication header injection
 * - Comprehensive error handling
 * - Request/response interceptors
 * - TypeScript type safety
 * - Retry logic for transient failures
 */

import { getEnvironmentConfig } from '@/config/environments';

/**
 * API Response wrapper for consistent error handling
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    timestamp: string;
    requestId?: string;
  };
}

/**
 * API Client configuration
 */
interface ApiClientConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

/**
 * Request options
 */
interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  timeout?: number;
  retries?: number;
}

/**
 * Core API Client class
 */
class ApiClient {
  private config: ApiClientConfig;
  private authToken: string | null = null;

  constructor() {
    const envConfig = getEnvironmentConfig();
    this.config = {
      baseUrl: envConfig.api.base,
      timeout: 30000, // 30s timeout for AWS (models loading)
      retryAttempts: 3,
      retryDelay: 1000,
    };

    // Load auth token from localStorage on init
    if (typeof window !== 'undefined') {
      this.authToken = localStorage.getItem('token');
    }
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string | null): void {
    this.authToken = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('token', token);
      } else {
        localStorage.removeItem('token');
      }
    }
  }

  /**
   * Get authentication token
   */
  getAuthToken(): string | null {
    return this.authToken;
  }

  /**
   * Build full URL from path
   */
  private buildUrl(path: string): string {
    // Remove leading slash if present
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    // Remove trailing slash from baseUrl if present
    const cleanBase = this.config.baseUrl.endsWith('/')
      ? this.config.baseUrl.slice(0, -1)
      : this.config.baseUrl;
    return `${cleanBase}/${cleanPath}`;
  }

  /**
   * Build request headers
   */
  private buildHeaders(options: RequestOptions): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add existing headers
    if (options.headers) {
      const existingHeaders = new Headers(options.headers);
      existingHeaders.forEach((value, key) => {
        headers[key] = value;
      });
    }

    // Add auth token if available and not skipped
    if (!options.skipAuth && this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  /**
   * Handle API errors consistently
   */
  private async handleError(response: Response): Promise<ApiResponse> {
    let errorMessage = 'An unexpected error occurred';
    let errorCode = 'UNKNOWN_ERROR';
    let errorDetails = null;

    try {
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
        errorCode = errorData.code || `HTTP_${response.status}`;
        errorDetails = errorData;
      } else {
        errorMessage = await response.text();
      }
    } catch (e) {
      console.error('Error parsing error response:', e);
    }

    return {
      success: false,
      error: {
        code: errorCode,
        message: errorMessage,
        details: errorDetails,
      },
      meta: {
        timestamp: new Date().toISOString(),
      },
    };
  }

  /**
   * Core request method with retry logic
   */
  private async makeRequest<T>(
    path: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const url = this.buildUrl(path);
    const maxRetries = options.retries ?? this.config.retryAttempts;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeout = options.timeout ?? this.config.timeout;
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(url, {
          ...options,
          headers: this.buildHeaders(options),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Success response
        if (response.ok) {
          const contentType = response.headers.get('content-type');
          let data: T;

          if (contentType?.includes('application/json')) {
            data = await response.json();
          } else {
            data = (await response.text()) as any;
          }

          const requestId = response.headers.get('x-request-id');
          return {
            success: true,
            data,
            meta: {
              timestamp: new Date().toISOString(),
              ...(requestId ? { requestId } : {}),
            },
          };
        }

        // Handle 401 Unauthorized - clear token
        if (response.status === 401) {
          this.setAuthToken(null);
          return this.handleError(response);
        }

        // Handle other errors
        if (response.status >= 500 && attempt < maxRetries) {
          // Retry on 5xx errors
          await new Promise((resolve) =>
            setTimeout(resolve, this.config.retryDelay * (attempt + 1))
          );
          continue;
        }

        return this.handleError(response);
      } catch (error) {
        lastError = error as Error;

        // Don't retry on network errors if it's the last attempt
        if (attempt === maxRetries) {
          break;
        }

        // Retry on network errors
        await new Promise((resolve) =>
          setTimeout(resolve, this.config.retryDelay * (attempt + 1))
        );
      }
    }

    // All retries failed
    return {
      success: false,
      error: {
        code: 'NETWORK_ERROR',
        message: lastError?.message || 'Network request failed',
        details: lastError,
      },
      meta: {
        timestamp: new Date().toISOString(),
      },
    };
  }

  /**
   * GET request
   */
  async get<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(path, {
      ...options,
      method: 'GET',
    });
  }

  /**
   * POST request
   */
  async post<T>(
    path: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const requestBody = body ? JSON.stringify(body) : null;
    return this.makeRequest<T>(path, {
      ...options,
      method: 'POST',
      ...(requestBody ? { body: requestBody } : {}),
    });
  }

  /**
   * PUT request
   */
  async put<T>(
    path: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const requestBody = body ? JSON.stringify(body) : null;
    return this.makeRequest<T>(path, {
      ...options,
      method: 'PUT',
      ...(requestBody ? { body: requestBody } : {}),
    });
  }

  /**
   * PATCH request
   */
  async patch<T>(
    path: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const requestBody = body ? JSON.stringify(body) : null;
    return this.makeRequest<T>(path, {
      ...options,
      method: 'PATCH',
      ...(requestBody ? { body: requestBody } : {}),
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(path, {
      ...options,
      method: 'DELETE',
    });
  }
}

// Singleton instance
export const apiClient = new ApiClient();

// Export for testing/mocking
export { ApiClient };