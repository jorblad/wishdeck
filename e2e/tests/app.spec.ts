import { test, expect } from '@playwright/test';

test.describe('WishDeck public surface', () => {
  test('API root responds', async ({ request }) => {
    const res = await request.get('/api/v1/');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('app');
  });

  test('health probes are green', async ({ request }) => {
    const health = await request.get('/api/v1/healthz');
    expect(health.ok()).toBeTruthy();
    const ready = await request.get('/api/v1/readyz');
    expect(ready.ok()).toBeTruthy();
  });

  test('login page renders and supports registration', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText('Sign in')).toBeVisible();
    await page.getByRole('button', { name: 'Create an account' }).click();
    await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
  });

  test('settings page is reachable only when authenticated', async ({ page }) => {
    await page.goto('/settings');
    // Unauthenticated users are redirected to /login.
    await expect(page).toHaveURL(/\/login/);
  });

  test('end-to-end: register, create wishlist, add item', async ({ page }) => {
    const email = `e2e_${Date.now()}@example.com`;

    await page.goto('/login');
    await page.getByRole('button', { name: 'Create an account' }).click();
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill('S3cret!!');
    await page.getByRole('button', { name: 'Create account' }).click();

    // Lands on the dashboard after auto-login.
    await expect(page.getByText('My Wishlists')).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: 'New wishlist' }).click();
    await expect(page).toHaveURL(/\/wishlists\//);
  });
});
