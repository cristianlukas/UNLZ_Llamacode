'use strict';
const fs = require('fs');
const { chromium } = require('/home/cristian/Documentos/ChatGPT/peritosoft/peritosoft-linux-build/dist-electron-linux-v8/linux-unpacked/resources/app/node_modules/playwright');

const [endpoint, outPath] = process.argv.slice(2);
if (!endpoint || !outPath) throw new Error('usage: node web_fixture_client.js endpoint output.json');
const sites = ['northstar', 'cloudbox', 'fittrail'];
const expected = 'Cancellation confirmed. Auto-renew is off. Account, files, purchases and free plan remain.';
const now = () => Number(process.hrtime.bigint()) / 1e9;

(async () => {
  const result = { endpoint, startedAt: new Date().toISOString(), sites: [] };
  let browser;
  try {
    browser = await chromium.connectOverCDP(endpoint, { timeout: 15000 });
    const context = await browser.newContext();
    for (const site of sites) {
      const row = { site, passed: false };
      const start = now();
      const page = await context.newPage();
      try {
        page.setDefaultTimeout(15000);
        await page.goto(`http://127.0.0.1:8777/${site}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.locator('#manage').click();
        await page.locator('#cancel').click();
        await page.locator('#confirm').click();
        const observed = await page.locator('#status').textContent();
        row.observed = observed;
        row.passed = observed === expected;
      } catch (e) {
        row.error = `${e.name}: ${e.message}`.slice(0, 500);
      } finally {
        row.seconds = now() - start;
        result.sites.push(row);
        await page.close().catch(() => {});
      }
    }
    await context.close();
  } catch (e) {
    result.connectionError = `${e.name}: ${e.message}`.slice(0, 600);
  } finally {
    if (browser) await browser.close().catch(() => {});
    result.finishedAt = new Date().toISOString();
    result.passed = result.sites.length === sites.length && result.sites.every(x => x.passed);
    fs.writeFileSync(outPath, JSON.stringify(result, null, 2) + '\n');
  }
  process.exit(result.passed ? 0 : 2);
})().catch(e => { fs.writeFileSync(outPath, JSON.stringify({ fatal: String(e) }) + '\n'); process.exit(3); });
