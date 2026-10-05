import { test, expect } from '@playwright/test';

test('umami analytics script is injected from public settings', async ({ page }) => {
  // First registrant becomes admin.
  const email = `umami_${Date.now()}@example.com`;
  await page.goto('/login');
  await page.getByRole('button', { name: 'Create an account' }).click();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill('S3cret!!');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByText('My Wishlists')).toBeVisible({ timeout: 10000 });

  // Configure Umami via the admin settings API (authenticated request).
  const src = 'https://analytics.example.com/script.js';
  const resp = await page.request.put('/api/v1/settings', {
    data: { values: { UMAMI_SRC: src, UMAMI_ID: 'site-abc-123' } },
  });
  expect(resp.status()).toBe(200);

  // Reload so the analytics boot picks up the new public settings.
  await page.goto('/');
  const script = page.locator('#umami-analytics');
  await expect(script).toHaveAttribute('data-website-id', 'site-abc-123');
  await expect(script).toHaveAttribute('src', src);
});
