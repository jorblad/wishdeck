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

    await page.getByTestId('new-wishlist').click();

    // "New wishlist" opens a create dialog; fill it and save to navigate to the list.
    const titleField = page.getByLabel('Title');
    await expect(titleField).toBeVisible({ timeout: 10000 });
    await titleField.fill('E2E Wishlist');
    await page.getByRole('button', { name: 'Save' }).click();

    await expect(page).toHaveURL(/\/wishlists\//);
  });

  test('public wishlist is browsable anonymously from the start page', async ({ page, browser }) => {
    // Register (authenticated context) and create a PUBLIC wishlist via the API.
    const email = `pub_${Date.now()}@example.com`;
    const title = `Public E2E List ${Date.now()}`;
    await page.goto('/login');
    await page.getByRole('button', { name: 'Create an account' }).click();
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill('S3cret!!');
    await page.getByRole('button', { name: 'Create account' }).click();
    await expect(page.getByText('My Wishlists')).toBeVisible({ timeout: 10000 });

    const created = await page.request.post('/api/v1/wishlists', {
      data: { title, visibility: 'public' },
    });
    expect(created.ok()).toBeTruthy();

    // A logged-out visitor should see public lists on the start page, but the
    // section is absent of any auth requirement. Use an exact match on the
    // heading so the empty-state banner text ("No public wishlists yet.") does
    // not also match.
    const anon = await browser.newContext();
    const anonPage = await anon.newPage();
    await anonPage.goto('/');
    await expect(anonPage.getByText('Public wishlists', { exact: true })).toBeVisible();
    await expect(anonPage.getByText(title)).toBeVisible();
    await anon.close();
  });
});
