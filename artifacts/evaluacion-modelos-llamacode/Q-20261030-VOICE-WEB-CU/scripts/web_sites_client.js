'use strict';
const fs = require('fs');
const { chromium } = require('/home/cristian/Documentos/ChatGPT/peritosoft/peritosoft-linux-build/dist-electron-linux-v8/linux-unpacked/resources/app/node_modules/playwright');
const [endpoint, outPath] = process.argv.slice(2);
if (!endpoint || !outPath) throw new Error('usage: node web_sites_client.js endpoint output.json');
const urls = [
  'https://example.com/', 'https://www.wikipedia.org/', 'https://www.python.org/',
  'https://docs.python.org/3/', 'https://www.rust-lang.org/',
  'https://developer.mozilla.org/en-US/docs/Web/JavaScript', 'https://github.com/',
  'https://pypi.org/', 'https://www.npmjs.com/', 'https://huggingface.co/',
  'https://pytorch.org/', 'https://arxiv.org/', 'https://www.w3.org/',
  'https://www.sqlite.org/', 'https://www.debian.org/', 'https://www.kernel.org/',
  'https://www.gnu.org/', 'https://stackoverflow.com/',
  'https://news.ycombinator.com/', 'https://www.openstreetmap.org/'
];
const now = () => Number(process.hrtime.bigint()) / 1e9;
(async () => {
  const result = { endpoint, startedAt: new Date().toISOString(), pages: [] };
  let browser;
  try {
    browser = await chromium.connectOverCDP(endpoint, { timeout: 15000 });
    const context = await browser.newContext();
    for (const url of urls) {
      const row = { url, passed: false };
      const start = now();
      let page;
      try {
        page = await context.newPage();
        const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
        row.status = response ? response.status() : null;
        row.finalUrl = page.url();
        row.title = await page.title();
        row.bodyLength = (await page.locator('body').innerText({ timeout: 3000 })).length;
        row.passed = !!row.status && row.status < 400 && !!row.title && row.bodyLength >= 50;
      } catch (e) {
        row.error = `${e.name}: ${e.message}`.slice(0, 500);
      } finally {
        row.seconds = now() - start;
        result.pages.push(row);
        if (page) await page.close().catch(() => {});
      }
    }
    await context.close();
  } catch (e) {
    result.connectionError = `${e.name}: ${e.message}`.slice(0, 600);
  } finally {
    if (browser) await browser.close().catch(() => {});
    result.finishedAt = new Date().toISOString();
    fs.writeFileSync(outPath, JSON.stringify(result, null, 2) + '\n');
  }
  process.exit(result.pages.length === urls.length ? 0 : 2);
})().catch(e => { fs.writeFileSync(outPath, JSON.stringify({ fatal: String(e) }) + '\n'); process.exit(3); });
