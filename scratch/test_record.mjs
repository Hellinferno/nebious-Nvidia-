import { chromium } from 'playwright-core';
import fs from 'fs';

async function main() {
  if (!fs.existsSync('recordings/raw')) {
    fs.mkdirSync('recordings/raw', { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: 'recordings/raw',
      size: { width: 1280, height: 720 }
    }
  });

  const page = await context.newPage();
  await page.goto('https://benchproof.vercel.app', { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);
  
  await context.close();
  await browser.close();

  const files = fs.readdirSync('recordings/raw');
  console.log('Recorded video files:', files);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
