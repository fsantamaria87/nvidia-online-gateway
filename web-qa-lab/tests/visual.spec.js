import { test, expect } from '@playwright/test';

test.describe('Visual QA', () => {
  test('no horizontal page overflow', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const dims = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth
    }));
    expect(dims.scroll, 'page should not produce horizontal overflow').toBeLessThanOrEqual(dims.viewport + 2);
  });

  test('capture release-candidate full page', async ({ page }, testInfo) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const path = testInfo.outputPath('release-candidate.png');
    await page.screenshot({ path, fullPage: true });

    await expect(page.locator('body')).toBeVisible();
  });

  test('critical text is not clipped by fixed headers', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const clipped = await page.locator('h1, h2, h3, th, [role="heading"]').evaluateAll(nodes =>
      nodes.filter(node => {
        const r = node.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) return false;
        return r.top < 0 || r.left < 0 || r.right > innerWidth + 2;
      }).slice(0, 20).map(node => (node.textContent || '').trim().slice(0, 100))
    );

    expect(clipped, 'important headings should remain inside viewport').toEqual([]);
  });
});
