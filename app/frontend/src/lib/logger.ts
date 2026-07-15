/**
 * Application Logger
 * Centralized logging utility with environment-aware output
 */

import { APP_CONFIG } from './config';

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  data?: any;
  timestamp: string;
  source?: string;
}

class Logger {
  private logLevel: LogLevel = APP_CONFIG.isDevelopment ? 'debug' : 'error';

  private formatMessage(level: LogLevel, message: string, data?: any, source?: string): LogEntry {
    return {
      level,
      message,
      data,
      timestamp: new Date().toISOString(),
      source,
    };
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: Record<LogLevel, number> = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3,
    };

    return levels[level] >= levels[this.logLevel];
  }

  private output(entry: LogEntry): void {
    if (!this.shouldLog(entry.level)) return;

    // In production, only log errors and send to monitoring
    if (APP_CONFIG.isProduction) {
      if (entry.level === 'error') {
        console.error(`[${entry.timestamp}] ${entry.source || 'APP'}:`, entry.message, entry.data);
        // TODO: Send to external monitoring service (e.g., Sentry, CloudWatch)
      }
      return;
    }

    // Development logging
    const prefix = `[${entry.timestamp}] ${entry.source || 'APP'}:`;
    
    switch (entry.level) {
      case 'debug':
        console.debug(prefix, entry.message, entry.data);
        break;
      case 'info':
        console.info(prefix, entry.message, entry.data);
        break;
      case 'warn':
        console.warn(prefix, entry.message, entry.data);
        break;
      case 'error':
        console.error(prefix, entry.message, entry.data);
        break;
    }
  }

  debug(message: string, data?: any, source?: string): void {
    this.output(this.formatMessage('debug', message, data, source));
  }

  info(message: string, data?: any, source?: string): void {
    this.output(this.formatMessage('info', message, data, source));
  }

  warn(message: string, data?: any, source?: string): void {
    this.output(this.formatMessage('warn', message, data, source));
  }

  error(message: string, data?: any, source?: string): void {
    this.output(this.formatMessage('error', message, data, source));
  }

  // Specialized API logging
  apiRequest(endpoint: string, method: string, data?: any): void {
    this.debug(`API ${method} ${endpoint}`, data, 'API');
  }

  apiResponse(endpoint: string, status: number, data?: any): void {
    if (status >= 400) {
      this.error(`API ${endpoint} failed with status ${status}`, data, 'API');
    } else {
      this.debug(`API ${endpoint} success (${status})`, data, 'API');
    }
  }

  apiError(endpoint: string, error: Error): void {
    this.error(`API ${endpoint} error: ${error.message}`, { stack: error.stack }, 'API');
  }

  // Component lifecycle logging
  componentMount(componentName: string): void {
    this.debug(`Component mounted: ${componentName}`, undefined, 'COMPONENT');
  }

  componentError(componentName: string, error: Error): void {
    this.error(`Component error in ${componentName}: ${error.message}`, { stack: error.stack }, 'COMPONENT');
  }
}

// Export singleton instance
export const logger = new Logger();

// Export types
export type { LogLevel, LogEntry };

export default logger;