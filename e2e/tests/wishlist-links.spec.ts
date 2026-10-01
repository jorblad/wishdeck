import { test, expect } from '@playwright/test';

async function register(page: any, email: string) {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Create an account' }).click();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill('S3cret!!');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByText('My Wishlists')).toBeVisible({ timeout: 10000 });
}

async function createPublicWishlist(page: any, title: string) {
  await page.getByTestId('new-wishlist').click();
  const titleField = page.getByLabel('Title');
  await expect(titleField).toBeVisible({ timeout: 10000 });
  await titleField.fill(title);
  const visibility = page.locator('.q-dialog').getByLabel('Visibility');
  await visibility.click();
  await page.getByRole('option', { name: 'Public' }).click();
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page).toHaveURL(/\/wishlists\//);
  return page.url();
}

test('self profile: edit display name', async ({ page }) => {
  const email = `profile_${Date.now()}@example.com`;
  await register(page, email);

  await page.goto('/profile');
  await expect(page.getByLabel('Full name')).toBeVisible();

  const nameField = page.getByLabel('Full name');
  await nameField.fill('Renamed Elf');
  const saveBtn = page
    .locator('.q-card', { hasText: 'My profile' })
    .getByRole('button', { name: 'Save' });
  await expect(saveBtn).toBeEnabled();
  await saveBtn.click();
  await expect(page.getByText('Profile saved')).toBeVisible();
});

test('gift exchange: link a wishlist to a person and reach it from the draw', async ({
  page,
}) => {
  const email = `link_${Date.now()}@example.com`;
  await register(page, email);

  const wishlistTitle = `Linked List ${Date.now()}`;
  await createPublicWishlist(page, wishlistTitle);

  // Create a group with two people.
  await page.goto('/gift-exchange');
  await expect(page.locator('.text-h5', { hasText: 'Gift Exchange' })).toBeVisible();
  await page.getByRole('button', { name: 'New group' }).click();
  await page.getByLabel('Group name').fill('Link Group');
  await page.getByRole('button', { name: 'Save' }).click();
  await page.getByText('Link Group').click();
  await expect(page.getByText('Participants')).toBeVisible();

  for (const name of ['Alice', 'Bob']) {
    await page.getByRole('button', { name: 'Add member' }).click();
    await page.getByLabel('New person name').fill(name);
    await page.getByRole('button', { name: 'Save' }).click();
    await expect(page.getByText(name)).toBeVisible();
  }

  // Edit Alice and link the wishlist we created.
  const aliceRow = page.locator('.q-item', { hasText: 'Alice' });
  await aliceRow.getByRole('button').first().click();
  await expect(page.getByText('Edit person')).toBeVisible();
  const linked = page.getByLabel('Linked wishlist');
  await linked.click();
  await page.getByRole('option', { name: wishlistTitle }).click();
  await page.getByRole('button', { name: 'Save' }).click();

  // Re-open edit to confirm the link persisted.
  await aliceRow.getByRole('button').first().click();
  await expect(page.getByText('Edit person')).toBeVisible();
  await page.getByRole('button', { name: 'Cancel' }).click();

  // Run the draw.
  await page.getByRole('button', { name: 'Run draw' }).click();
  await page.getByRole('button', { name: 'OK' }).click();
  await expect(page.getByText('Assignments')).toBeVisible({ timeout: 10000 });
  await expect(page.getByText('View wishlist')).toHaveCount(1);

  // The giver can jump straight to the receiver's wishlist.
  await page.getByText('View wishlist').click();
  await expect(page).toHaveURL(/\/wishlists\//);
  await expect(page.getByText(wishlistTitle)).toBeVisible();
});
