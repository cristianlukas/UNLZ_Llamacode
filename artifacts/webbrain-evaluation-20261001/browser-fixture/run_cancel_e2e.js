// Start site_server.py separately, then run with Playwright 1.62.1 and Chrome.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: false,
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox'],
  });
  const results = [];
  for (const [site, path] of [
    ['northstar', '/northstar'],
    ['cloudbox', '/cloudbox'],
    ['fittrail', '/fittrail'],
  ]) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(`http://127.0.0.1:8777${path}`);
    await page.getByRole('button', { name: 'Manage plan' }).click();
    await page.getByRole('button', { name: 'Cancel renewal' }).click();
    await page.getByRole('button', { name: 'Confirm cancellation' }).click();
    const status = await page.locator('#status').innerText();
    const passed = /cancellation confirmed/i.test(status)
      && /auto-renew is off/i.test(status)
      && /account, files, purchases and free plan remain/i.test(status);
    results.push({ site, status, passed });
    if (site === 'northstar')
      await page.screenshot({ path: 'artifacts/webbrain-evaluation-20261001/browser-fixture/northstar-cancelled.png' });
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify({ allPassed: results.every((x) => x.passed), results }, null, 2));
  if (results.some((x) => !x.passed)) process.exitCode = 1;
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
