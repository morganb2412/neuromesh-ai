import { expect, test } from '@playwright/test';

test('live OpenAlex work flows through graph inspection and cited assistant answer', async ({page})=>{
  test.skip(process.env.NEUROMESH_LIVE_INTEGRATION !== '1', 'requires an explicitly ingested local OpenAlex database');
  const response=await page.request.get('/api/graph');
  expect(response.ok()).toBe(true);
  const graph=await response.json();
  const paper=graph.nodes.find((node:any)=>node.kind==='PAPER'&&graph.edges.some((edge:any)=>edge.source_id===node.id&&edge.kind==='AUTHORED_BY'));
  expect(paper).toBeTruthy();
  const authors=graph.edges.filter((edge:any)=>edge.source_id===paper.id&&edge.kind==='AUTHORED_BY');
  const author=graph.nodes.find((node:any)=>node.id===authors[0].target_id);
  expect(graph.evidence[authors[0].evidence_id].url).toMatch(/^https:\/\/openalex\.org\/W\d+$/);

  await page.goto('/');
  await page.getByRole('button',{name:'Research',exact:true}).click();
  await page.getByRole('textbox',{name:'Search public records'}).fill(paper.label);
  await page.getByRole('button',{name:'Locate in graph'}).first().click();
  await expect(page.locator('.entity-inspector')).toContainText('AUTHORED BY');
  await page.getByRole('textbox',{name:'Research question'}).fill(`Who authored ${paper.label}?`);
  await page.getByTitle('Send question').click();
  await expect(page.locator('.message.assistant').last()).toContainText(author.label);
  await expect(page.locator('.message.assistant').last().locator('a[href^="https://openalex.org/W"]').first()).toBeVisible();
  await expect(page.locator('.investigation-state')).toContainText(/cited records/);
});
