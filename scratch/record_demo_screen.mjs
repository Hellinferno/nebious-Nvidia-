import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function injectCursor(page) {
  await page.evaluate(() => {
    if (document.getElementById('__cursor__')) return;
    const c = document.createElement('div');
    c.id = '__cursor__';
    c.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.7);
      border: 2px solid #ffffff;
      box-shadow: 0 0 10px rgba(16, 185, 129, 0.9);
      pointer-events: none;
      z-index: 2147483647;
      transform: translate(-50%, -50%);
      transition: transform 0.12s ease-out;
    `;
    document.body.appendChild(c);
  });
}

let curX = 640;
let curY = 360;

async function moveMouse(page, targetX, targetY, steps = 25, delayMs = 15) {
  const startX = curX;
  const startY = curY;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    const x = Math.round(startX + (targetX - startX) * ease);
    const y = Math.round(startY + (targetY - startY) * ease);
    await page.mouse.move(x, y);
    await page.evaluate(({ x, y }) => {
      const c = document.getElementById('__cursor__');
      if (c) {
        c.style.left = `${x}px`;
        c.style.top = `${y}px`;
      }
    }, { x, y });
    await sleep(delayMs);
  }
  curX = targetX;
  curY = targetY;
}

async function clickMouse(page) {
  await page.evaluate(() => {
    const c = document.getElementById('__cursor__');
    if (c) c.style.transform = 'translate(-50%, -50%) scale(0.6)';
  });
  await sleep(100);
  await page.mouse.down();
  await sleep(60);
  await page.mouse.up();
  await page.evaluate(() => {
    const c = document.getElementById('__cursor__');
    if (c) c.style.transform = 'translate(-50%, -50%) scale(1)';
  });
  await sleep(150);
}

async function smoothScroll(page, targetY, steps = 25, delayMs = 20) {
  const currentY = await page.evaluate(() => window.scrollY);
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    const y = Math.round(currentY + (targetY - currentY) * ease);
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await sleep(delayMs);
  }
}

async function record() {
  const demoOwner = process.env.BENCHPROOF_DEMO_OWNER;
  const demoTask = process.env.BENCHPROOF_DEMO_TASK;
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(demoOwner ?? '') || !/^coding-[a-f0-9]{16}$/.test(demoTask ?? '')) {
    throw new Error('Set a private sample owner capability and completed demo task in the process environment before recording');
  }
  const rawDir = path.resolve('recordings/raw');
  if (!fs.existsSync(rawDir)) {
    fs.mkdirSync(rawDir, { recursive: true });
  }

  for (const f of fs.readdirSync(rawDir)) {
    if (f.endsWith('.webm')) {
      fs.unlinkSync(path.join(rawDir, f));
    }
  }

  console.log('Launching browser for synced recording...');
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: rawDir,
      size: { width: 1280, height: 720 }
    }
  });

  const page = await context.newPage();

  // ==========================================
  // SCENE 1: Introduction (0.00s -> 24.82s: 24.8s)
  // ==========================================
  console.log('--- SCENE 1: Intro (0s - 25s) ---');
  await page.goto('https://benchproof.vercel.app', { waitUntil: 'networkidle' });
  await injectCursor(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(1000);

  // Hover over topbar branding
  await moveMouse(page, 150, 40, 25, 20);
  await sleep(2000);

  // Highlight provider status & badges
  await moveMouse(page, 760, 40, 25, 20);
  await sleep(1500);

  // Open Commands palette
  await moveMouse(page, 890, 40, 25, 20);
  await sleep(500);
  await clickMouse(page);
  await injectCursor(page);
  await sleep(3500);

  // Hover through commands
  await moveMouse(page, 640, 260, 20, 20);
  await sleep(1500);
  await moveMouse(page, 640, 330, 20, 20);
  await sleep(1500);

  // Close palette with Escape
  await page.keyboard.press('Escape');
  await sleep(800);

  // Hover over hero title
  await moveMouse(page, 320, 280, 25, 20);
  await sleep(2500);

  // Hover over architecture guarantee pills
  await moveMouse(page, 220, 440, 25, 20);
  await sleep(2000);
  await moveMouse(page, 440, 440, 25, 20);
  await sleep(2000);

  // ==========================================
  // SCENE 2: Intake & Protected Boundary (24.82s -> 45.81s: 21.0s)
  // ==========================================
  console.log('--- SCENE 2: Intake (25s - 46s) ---');
  await smoothScroll(page, 350, 20, 20);
  await sleep(800);

  // Click StringCalculator chip
  await moveMouse(page, 120, 270, 25, 20);
  await sleep(600);
  await clickMouse(page);
  await sleep(1500);

  // Hover over app/calculator.py (EDIT)
  await moveMouse(page, 140, 520, 25, 20);
  await sleep(2000);

  // Hover over tests/test_calculator.py (TEST / LOCKED)
  await moveMouse(page, 140, 560, 25, 20);
  await sleep(2500);

  // Move right to task specification and starting point
  await moveMouse(page, 620, 320, 25, 20);
  await sleep(2500);

  // Scroll down to task draft button
  await smoothScroll(page, 650, 20, 20);
  await moveMouse(page, 620, 480, 25, 20);
  await sleep(2000);

  // Click Create task draft
  await moveMouse(page, 620, 580, 20, 20);
  await clickMouse(page);
  await sleep(2500);

  // Transition to active completed task
  await page.evaluate(({ owner, task }) => {
    localStorage.setItem('benchproof.owner-capability', owner);
    localStorage.setItem('benchproof.active-coding-task', task);
  }, { owner: demoOwner, task: demoTask });
  await page.reload({ waitUntil: 'networkidle' });
  await injectCursor(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(1500);

  // ==========================================
  // SCENE 3: Cryptographic Planning (45.81s -> 63.86s: 18.05s)
  // ==========================================
  console.log('--- SCENE 3: Plan (46s - 64s) ---');
  // Scroll down to "Review the plan" (top ~1650)
  await smoothScroll(page, 1400, 25, 20);
  await moveMouse(page, 200, 320, 25, 20);
  await sleep(2000);

  // Highlight step 1
  await moveMouse(page, 220, 390, 20, 20);
  await sleep(2500);

  // Highlight step 2
  await moveMouse(page, 220, 450, 20, 20);
  await sleep(2500);

  // Highlight step 3
  await moveMouse(page, 220, 510, 20, 20);
  await sleep(2500);

  // Highlight Plan Approval badge and cryptographic hash
  await moveMouse(page, 380, 320, 25, 20);
  await sleep(3500);

  // ==========================================
  // SCENE 4: Isolated Execution & Stepper (63.86s -> 87.39s: 23.53s)
  // ==========================================
  console.log('--- SCENE 4: Execution Stepper (64s - 87s) ---');
  // Scroll down to "Test results (3)" (top ~2065)
  await smoothScroll(page, 1800, 25, 20);
  await moveMouse(page, 200, 320, 25, 20);
  await sleep(2000);

  // Highlight Baseline check (Execution #1 - failing assertion)
  await moveMouse(page, 250, 420, 25, 20);
  await sleep(3500);

  // Highlight Candidate edit test (Execution #2 - patch applied)
  await moveMouse(page, 250, 500, 25, 20);
  await sleep(3500);

  // Highlight Final check (Execution #3 - 100% tests passed)
  await moveMouse(page, 250, 580, 25, 20);
  await sleep(3500);

  // Scroll back up to the Stepper and status header (top ~350)
  await smoothScroll(page, 350, 25, 20);
  await moveMouse(page, 500, 260, 25, 20);
  await sleep(3000);

  // Highlight REVIEW_READY badge in header
  await moveMouse(page, 440, 100, 25, 20);
  await sleep(3500);

  // ==========================================
  // SCENE 5: Unified Diff & Checkpoints (87.39s -> 103.60s: 16.21s)
  // ==========================================
  console.log('--- SCENE 5: Unified Diff & Checkpoints (87s - 104s) ---');
  // Scroll to "Code changes" diff viewer (top ~1040, right column)
  await smoothScroll(page, 850, 25, 20);
  await moveMouse(page, 750, 280, 25, 20);
  await sleep(2000);

  // Trace through green added lines in diff
  await moveMouse(page, 780, 430, 25, 20);
  await sleep(3000);
  await moveMouse(page, 780, 480, 25, 20);
  await sleep(2500);

  // Scroll down to Checkpoints (5) (top ~1734, right column)
  await smoothScroll(page, 1550, 25, 20);
  await moveMouse(page, 750, 280, 25, 20);
  await sleep(2500);

  // Hover over rollback buttons
  await moveMouse(page, 1150, 360, 20, 20);
  await sleep(2500);

  // ==========================================
  // SCENE 6: Evidence Bundle & Summary (103.60s -> 123.28s: 19.68s)
  // ==========================================
  console.log('--- SCENE 6: Bundle & Wrap-up (104s - 123s) ---');
  // Scroll to "Download your work" (top ~1504, right column)
  await smoothScroll(page, 1300, 25, 20);
  await moveMouse(page, 750, 280, 25, 20);
  await sleep(1500);

  // Hover and click "⬇ Download Complete Bundle (.zip)"
  await moveMouse(page, 780, 380, 25, 20);
  await sleep(1000);
  await clickMouse(page);
  await sleep(2500);

  // Scroll down to Activity (24) event trace
  await smoothScroll(page, 1950, 25, 20);
  await moveMouse(page, 750, 350, 25, 20);
  await sleep(3000);

  // Smoothly scroll back to the top of the workspace
  await smoothScroll(page, 0, 35, 15);
  await moveMouse(page, 300, 260, 25, 20);
  await sleep(4000);

  console.log('Recording finished, saving video...');
  await context.close();
  await browser.close();

  const files = fs.readdirSync(rawDir).filter(f => f.endsWith('.webm'));
  console.log('Recorded video files in raw:', files);
  if (files.length > 0) {
    fs.copyFileSync(path.join(rawDir, files[0]), 'recordings/raw_walkthrough.webm');
    console.log('Saved: recordings/raw_walkthrough.webm');
  }
}

record().catch(err => {
  console.error('Recording error:', err);
  process.exit(1);
});
