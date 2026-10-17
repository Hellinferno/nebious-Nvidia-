import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const profile = path.resolve(process.argv[2]);
const url = new URL(process.argv[3]);
assert.ok((url.protocol === 'https:' && url.hostname.endsWith('.vercel.app')) || (url.protocol === 'http:' && url.hostname === '127.0.0.1'));
const output = path.dirname(profile);
const port = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0];
const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json());
const socket = new WebSocket(targets.find(item => item.type === 'page').webSocketDebuggerUrl);
await once(socket, 'open');
const pending = new Map();
const exceptions = [];
let sequence = 0;
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
  if (!message.id) return;
  const task = pending.get(message.id);
  if (!task) return;
  pending.delete(message.id);
  clearTimeout(task.timer);
  if (message.error) task.reject(new Error(message.error.message));
  else task.resolve(message.result);
});
function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timed out: ${method}`)); }, 120_000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  assert.ok(!result.exceptionDetails, result.exceptionDetails?.text);
  return result.result.value;
}
async function waitFor(expression) {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  throw new Error(`Timed out waiting for ${expression}`);
}
async function screenshot(name) {
  const result = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await writeFile(path.join(output, name), Buffer.from(result.data, 'base64'));
}
const evidence = { schema: 'benchproof/ui-layout-check-v1', timestamp: new Date().toISOString(), url: url.origin, viewports: [], verified: false };
try {
  await mkdir(output, { recursive: true });
  await command('Page.enable');
  await command('Runtime.enable');
  await command('DOM.enable');
  await command('CSS.enable');
  await command('Page.navigate', { url: url.href });
  await waitFor("document.querySelectorAll('.example-card').length === 5 && /Worker\\s+alive/i.test(document.body.innerText)");
  const document = await command('DOM.getDocument');
  evidence.renderedFonts = {};
  for (const selector of ['h1', '.brand', '.subtitle', '.next-action > strong']) {
    const element = await command('DOM.querySelector', { nodeId: document.root.nodeId, selector });
    evidence.renderedFonts[selector] = (await command('CSS.getPlatformFontsForNode', { nodeId: element.nodeId })).fonts;
  }
  for (const width of [1440, 1280, 1024, 768, 390, 320]) {
    await command('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width < 600 });
    await evaluate('document.fonts.ready.then(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))');
    const layout = await evaluate(`(() => {
      const heading = document.querySelector('h1');
      const subtitle = document.querySelector('.subtitle');
      const font = getComputedStyle(document.body).fontFamily;
      const overflow = [...document.querySelectorAll('.panel, .example-card, .btn, .status-strip, .topbar')].filter(element => {
        const rectangle = element.getBoundingClientRect();
        return rectangle.width && (rectangle.right > innerWidth + 1 || rectangle.left < -1);
      }).map(element => element.className);
      return { width: innerWidth, documentWidth: document.documentElement.scrollWidth, font, headingLineHeight: parseFloat(getComputedStyle(heading).lineHeight), headingFontSize: parseFloat(getComputedStyle(heading).fontSize), headingBottom: heading.getBoundingClientRect().bottom, subtitleTop: subtitle.getBoundingClientRect().top, overflow };
    })()`);
    assert.match(layout.font, /Segoe UI/);
    assert.ok(layout.headingLineHeight > layout.headingFontSize, 'Heading line box must not clip or overlap');
    assert.ok(layout.headingBottom <= layout.subtitleTop, 'Heading overlaps subtitle');
    assert.ok(layout.documentWidth <= width + 1, `Horizontal page overflow at ${width}px`);
    assert.deepEqual(layout.overflow, [], `Controls overflow at ${width}px`);
    evidence.viewports.push(layout);
    if (width === 1440 || width === 390) await screenshot(`workspace-${width}.png`);
  }
  await command('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'dark' }] });
  assert.equal(await evaluate("getComputedStyle(document.documentElement).colorScheme"), 'light');
  await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'k', code: 'KeyK', modifiers: 2, windowsVirtualKeyCode: 75 });
  await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'k', code: 'KeyK', modifiers: 2, windowsVirtualKeyCode: 75 });
  await waitFor("document.querySelector('[role=dialog]') && document.activeElement.matches('.palette-input')");
  assert.ok(await evaluate("document.querySelector('.palette').getBoundingClientRect().right <= innerWidth"));
  await command('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await command('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await waitFor("!document.querySelector('[role=dialog]')");
  assert.deepEqual(exceptions, []);
  Object.assign(evidence, { commandKeyboard: true, stableDarkPreference: true, exceptions, verified: true });
} catch (error) {
  evidence.failure = error.message;
  evidence.exceptions = exceptions;
  process.exitCode = 1;
} finally {
  const filename = path.join(output, `ui-check-${Date.now()}.json`);
  await writeFile(filename, JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify({ ...evidence, record: filename }, null, 2));
  await command('Browser.close').catch(() => {});
  socket.close();
}
