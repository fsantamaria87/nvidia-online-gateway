import { test, expect } from '@playwright/test';

test.describe('Release smoke gate', () => {
  test('app opens without fatal browser errors', async ({ page }) => {
    const consoleErrors = [];
    const pageErrors = [];

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => pageErrors.push(String(err)));

    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response, 'navigation should return a response').not.toBeNull();
    expect(response.status(), 'entry page HTTP status').toBeLessThan(400);

    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('body')).not.toHaveText(/^\s*$/);

    expect(pageErrors, 'uncaught JavaScript errors').toEqual([]);
    expect(consoleErrors, 'console.error output').toEqual([]);
  });

  test('interactive controls do not overlap the viewport', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const offenders = await page.locator('button, a, input, select, textarea, [role="button"]').evaluateAll(nodes =>
      nodes
        .filter(el => {
          const r = el.getBoundingClientRect();
          const s = getComputedStyle(el);
          return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
        })
        .filter(el => {
          const r = el.getBoundingClientRect();
          return r.right < 0 || r.bottom < 0 || r.left > innerWidth || r.top > innerHeight;
        })
        .slice(0, 20)
        .map(el => ({
          tag: el.tagName,
          text: (el.textContent || '').trim().slice(0, 80),
          id: el.id || null
        }))
    );

    expect(offenders, 'visible interactive controls outside viewport').toEqual([]);
  });

  test('focusable controls have visible focus feedback', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const focusables = page.locator('button:visible, a[href]:visible, input:visible, select:visible, textarea:visible');
    const count = Math.min(await focusables.count(), 12);

    for (let i = 0; i < count; i++) {
      const el = focusables.nth(i);
      await el.focus();
      const focusVisible = await el.evaluate(node => {
        const s = getComputedStyle(node);
        return s.outlineStyle !== 'none' || s.boxShadow !== 'none' || s.borderColor !== 'rgba(0, 0, 0, 0)';
      });
      expect(focusVisible, 'focus feedback should be perceivable').toBeTruthy();
    }
  });
});
