import { test, expect } from '@playwright/test';

test.describe('Gift exchange', () => {
  test('register, create group, add members, run draw', async ({ page }) => {
    const email = `ge_${Date.now()}@example.com`;

    // Register + auto-login (same flow as the core e2e path).
    await page.goto('/login');
    await page.getByRole('button', { name: 'Create an account' }).click();
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill('S3cret!!');
    await page.getByRole('button', { name: 'Create account' }).click();
    await expect(page.getByText('My Wishlists')).toBeVisible({ timeout: 10000 });

    // The module is enabled in the e2e stack.
    await page.goto('/gift-exchange');
    await expect(page.getByText('Gift Exchange')).toBeVisible();

    // Create a group.
    await page.getByRole('button', { name: 'New group' }).click();
    const groupName = page.getByLabel('Group name');
    await expect(groupName).toBeVisible();
    await groupName.fill('Family 2026');
    await page.getByRole('button', { name: 'Save' }).click();

    await expect(page.getByText('Family 2026')).toBeVisible();
    await page.getByText('Family 2026').click();

    // Group detail shows the member manager.
    await expect(page.getByText('Participants')).toBeVisible();

    // Add three people across two families (siblings A + cousin B).
    const addBtn = page.getByRole('button', { name: 'Add member' });
    const people = [
      { name: 'Alice', family: 'A' },
      { name: 'Bob', family: 'A' },
      { name: 'Cousin', family: 'B' },
    ];
     for (const p of people) {
       await addBtn.click();
       await page.getByLabel('New person name').fill(p.name);
       const fam = page.getByLabel('Family');
       await fam.click();
       await fam.pressSequentially(p.family);
       await fam.press('Enter');
       await page.getByRole('button', { name: 'Save' }).click();
     }
     for (const p of people) {
       await expect(page.getByText(p.name)).toBeVisible();
     }

     // Run the draw and confirm.
     await page.getByRole('button', { name: 'Run draw' }).click();
     await page.getByRole('button', { name: 'OK' }).click();

     // Assignments are shown (one "gives to" line per member).
     await expect(page.getByText('Assignments')).toBeVisible({ timeout: 10000 });
     await expect(page.getByText(/gives to/)).toBeVisible();

     // People directory: switch tab and add a global person.
     await page.goto('/gift-exchange');
     await expect(page.getByText('Gift Exchange')).toBeVisible();
     await page.getByRole('tab', { name: 'People' }).click();
     await page.getByRole('button', { name: 'Add person' }).click();
     await page.getByLabel('Name').fill('Global Person');
     await page.getByRole('button', { name: 'Save' }).click();
     await expect(page.getByText('Global Person')).toBeVisible();

     // The group also shows up as a card on the start page.
     await page.goto('/');
     await expect(page.getByText('Family 2026')).toBeVisible();
   });
});
