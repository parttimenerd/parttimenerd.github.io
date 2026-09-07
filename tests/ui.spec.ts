import { test, expect } from '@playwright/test';

const JVM_TOOLS = '/jvm-tools/';

// ── helpers ──────────────────────────────────────────────────────────────────

async function setTheme(page: any, theme: 'light' | 'dark') {
  await page.evaluate((t: string) => {
    localStorage.setItem('theme', t);
    document.documentElement.setAttribute('data-theme', t);
  }, theme);
}

// ── theme toggle ─────────────────────────────────────────────────────────────

test.describe('theme toggle', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(JVM_TOOLS);
    // start from a known light state
    await setTheme(page, 'light');
    await page.reload();
  });

  test('clicking toggle switches to dark', async ({ page }) => {
    await page.click('#theme-toggle');
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('dark');
  });

  test('clicking toggle twice returns to light', async ({ page }) => {
    await page.click('#theme-toggle');
    await page.click('#theme-toggle');
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('light');
  });

  test('theme persists across page reload', async ({ page }) => {
    await page.click('#theme-toggle'); // → dark
    await page.reload();
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme')
    );
    expect(theme).toBe('dark');
  });

  test('localStorage is updated on toggle', async ({ page }) => {
    await page.click('#theme-toggle');
    const stored = await page.evaluate(() => localStorage.getItem('theme'));
    expect(stored).toBe('dark');
  });

  test('sun icon visible in dark mode', async ({ page }) => {
    await page.click('#theme-toggle'); // → dark
    await expect(page.locator('#theme-icon-sun')).not.toHaveClass(/hidden/);
    await expect(page.locator('#theme-icon-moon')).toHaveClass(/hidden/);
  });

  test('moon icon visible in light mode', async ({ page }) => {
    // already light after beforeEach + reload
    await expect(page.locator('#theme-icon-moon')).not.toHaveClass(/hidden/);
    await expect(page.locator('#theme-icon-sun')).toHaveClass(/hidden/);
  });
});

// ── dark mode visual ──────────────────────────────────────────────────────────

test.describe('dark mode visual', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(JVM_TOOLS);
    await setTheme(page, 'dark');
    await page.reload();
  });

  test('page background is dark in dark mode', async ({ page }) => {
    const bg = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--page-bg').trim()
    );
    expect(bg).toBe('#0d1117');
  });

  test('code background is dark in dark mode', async ({ page }) => {
    const codeBg = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--code-bg').trim()
    );
    expect(codeBg).toBe('#161b22');
  });

  test('body text is light in dark mode', async ({ page }) => {
    const color = await page.evaluate(() =>
      getComputedStyle(document.body).color
    );
    // #e6edf3 = rgb(230,237,243)
    expect(color).toBe('rgb(230, 237, 243)');
  });

  test('project cards have dark background', async ({ page }) => {
    const card = page.locator('.project-card').first();
    await expect(card).toBeVisible();
    const bg = await card.evaluate((el: Element) =>
      getComputedStyle(el).backgroundColor
    );
    // #161b22 = rgb(22,27,34)
    expect(bg).toBe('rgb(22, 27, 34)');
  });
});

test.describe('light mode visual', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(JVM_TOOLS);
    await setTheme(page, 'light');
    await page.reload();
  });

  test('page background is light in light mode', async ({ page }) => {
    const bg = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--page-bg').trim()
    );
    expect(bg).toBe('#f9f9f8');
  });

  test('code background is light in light mode', async ({ page }) => {
    const codeBg = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--code-bg').trim()
    );
    expect(codeBg).toBe('#f3f4f6');
  });
});

// ── syntax highlighting ───────────────────────────────────────────────────────

test.describe('syntax highlighting', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(JVM_TOOLS);
    await setTheme(page, 'light');
    await page.reload();
  });

  test('bash code blocks in Install/Usage tabs get hljs class', async ({ page }) => {
    // Chroma blocks have data-lang; hljs processes the ones WITHOUT data-lang
    // Our shell-highlight.js sets className='hljs' on those blocks
    const shellBlocks = page.locator('pre code[data-raw-text]');
    const count = await shellBlocks.count();
    expect(count).toBeGreaterThan(0);
    // The shell highlighter sets className='hljs' after processing
    const firstBlock = shellBlocks.first();
    await expect(firstBlock).toHaveClass(/hljs/);
  });

  test('java code blocks get hljs class', async ({ page }) => {
    const javaBlocks = page.locator('pre code.language-java');
    const count = await javaBlocks.count();
    expect(count).toBeGreaterThan(0);
    const firstBlock = javaBlocks.first();
    await expect(firstBlock).toHaveClass(/hljs/);
  });

  test('java code blocks have colored spans (keywords highlighted)', async ({ page }) => {
    const javaBlock = page.locator('pre code.language-java').first();
    // highlight.js wraps keywords in spans with hljs- classes
    const keywordSpans = javaBlock.locator('span[class^="hljs-"], span[class*=" hljs-"]');
    const count = await keywordSpans.count();
    expect(count).toBeGreaterThan(0);
  });

  test('how_to chroma blocks have colored spans', async ({ page }) => {
    // Open all details so Chroma content is in the DOM and visible
    await page.evaluate(() => {
      document.querySelectorAll('details').forEach((d: HTMLDetailsElement) => d.setAttribute('open', ''));
    });

    // Chroma wraps tokens in spans with short class names: .cl, .m, .c1, .k etc
    // Look inside .chroma pre/code elements
    const chromaSpans = page.locator('.chroma code span[class]');
    const count = await chromaSpans.count();
    expect(count).toBeGreaterThan(0);
  });

  test('shell highlighting applies light colors in light mode', async ({ page }) => {
    const bashCode = page.locator('pre code[data-raw-text]').first();
    await expect(bashCode).toBeVisible();
    // In light mode, shell tokens use inline style with light palette
    const spans = bashCode.locator('span[style]');
    const count = await spans.count();
    expect(count).toBeGreaterThan(0);
    // Light mode: command color is #6f42c1 (purple), not dark-mode #DCDCAA
    const firstStyle = await spans.first().getAttribute('style');
    expect(firstStyle).not.toContain('#DCDCAA');
  });

  test('shell highlighting applies dark colors in dark mode', async ({ page }) => {
    await setTheme(page, 'dark');
    await page.reload();
    const bashCode = page.locator('pre code[data-raw-text]').first();
    await expect(bashCode).toBeVisible();
    const spans = bashCode.locator('span[style]');
    const firstStyle = await spans.first().getAttribute('style');
    // Dark mode command color is #DCDCAA
    expect(firstStyle).not.toContain('#6f42c1');
  });
});

// ── how_to accordion ──────────────────────────────────────────────────────────

test.describe('how_to accordion', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(JVM_TOOLS);
  });

  test('how_to details elements exist', async ({ page }) => {
    const details = page.locator('details');
    const count = await details.count();
    expect(count).toBeGreaterThan(0);
  });

  test('how_to summary is visible and clickable', async ({ page }) => {
    const summary = page.locator('details summary').first();
    await expect(summary).toBeVisible();
    await summary.click();
    const details = page.locator('details').first();
    await expect(details).toHaveAttribute('open', '');
  });

  test('how_to body renders prose content when open', async ({ page }) => {
    const details = page.locator('details').first();
    await details.evaluate((el: HTMLElement) => el.setAttribute('open', ''));
    // Body should have some text content beyond just the summary
    const bodyText = await details.evaluate((el: HTMLElement) => el.innerText);
    expect(bodyText.length).toBeGreaterThan(20);
  });

  test('how_to body has code block when open', async ({ page }) => {
    // Open all details to find one with a code block
    await page.evaluate(() => {
      document.querySelectorAll('details').forEach((d: HTMLDetailsElement) => d.setAttribute('open', ''));
    });
    // At least one details should contain a pre/code block
    const codeInDetails = page.locator('details pre').first();
    await expect(codeInDetails).toBeVisible();
  });
});
