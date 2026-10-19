import { chromium } from 'playwright-core';

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 }
  });

  console.log('Navigating to https://benchproof.vercel.app ...');
  await page.goto('https://benchproof.vercel.app', { waitUntil: 'networkidle' });
  console.log('Title:', await page.title());
  await page.screenshot({ path: 'recordings/landing_preview.png' });
  console.log('Saved recordings/landing_preview.png');
  await browser.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
