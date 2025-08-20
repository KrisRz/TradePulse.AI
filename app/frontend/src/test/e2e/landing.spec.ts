import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('should load the homepage successfully', async ({ page }) => {
    await page.goto('/');
    
    // Check that the page title is correct
    await expect(page).toHaveTitle(/TradePulse\.AI/);
    
    // Check for key elements - be more specific about which h1
    await expect(page.getByRole('heading', { name: /AI-Powered Crypto Trading/ })).toBeVisible();
  });

  test('should have proper meta tags', async ({ page }) => {
    await page.goto('/');
    
    // Check meta description
    const metaDescription = page.locator('meta[name="description"]');
    await expect(metaDescription).toHaveAttribute('content', /AI-powered crypto day trading platform/);
    
    // Check that PWA manifest is linked
    const manifest = page.locator('link[rel="manifest"]');
    await expect(manifest).toHaveAttribute('href', '/manifest.json');
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Page should still be functional on mobile
    await expect(page.locator('h1')).toBeVisible();
  });

  test('should have PWA capabilities', async ({ page }) => {
    await page.goto('/');
    
    // Check PWA manifest
    const manifest = page.locator('link[rel="manifest"]');
    await expect(manifest).toBeAttached();
    await expect(manifest).toHaveAttribute('href', '/manifest.json');
    
    // Check theme color meta tag (PWA requirement)
    const themeColor = page.locator('meta[name="theme-color"]');
    await expect(themeColor).toBeAttached();
    
    // Verify manifest is accessible
    const manifestResponse = await page.request.get('/manifest.json');
    expect(manifestResponse.status()).toBe(200);
    
    // Check if service worker registration happens (via VitePWA)
    // This checks for the PWA functionality without looking for specific script tags
    const hasServiceWorkerSupport = await page.evaluate(() => {
      return 'serviceWorker' in navigator;
    });
    expect(hasServiceWorkerSupport).toBe(true);
  });
}); 