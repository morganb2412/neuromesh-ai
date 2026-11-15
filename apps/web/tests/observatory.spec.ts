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

test('research and analytics show indexed measurements', async ({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Research',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Research.'})).toBeVisible();
  await expect(page.locator('.record-grid .workspace-card').first()).toBeVisible();
  await page.getByRole('button',{name:'Locate in graph'}).first().click();
  await expect(page.locator('.entity-inspector')).toBeVisible();
  await page.getByRole('button',{name:'Analytics',exact:true}).click();
  await expect(page.getByText('TF-IDF / PUBLIC RECORD TITLES')).toBeVisible();
  await expect(page.getByText('Dataset SHA-256:')).toBeVisible();
});
