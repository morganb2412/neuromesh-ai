import { expect, test } from '@playwright/test';

test('observatory renders and receives grounded investigation events', async ({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Intelligence, in motion/})).toBeVisible();
  await expect(page.locator('.dataset-badge')).toContainText(/DEMONSTRATION DATA|PUBLIC RECORDS/);
  await expect(page.locator('.graph-stage canvas')).toBeVisible();
  await expect(page.locator('.holo-canvas canvas')).toBeVisible();
  await page.getByRole('button',{name:'AI agent research'}).click();
  await expect(page.locator('.message.assistant')).toHaveCount(2);
  await expect(page.locator('.investigation-state')).toContainText(/cited records/);
});
