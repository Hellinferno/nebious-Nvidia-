import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createHash } from 'node:crypto';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const profile = path.resolve(process.argv[2]);
const url = new URL(process.argv[3]);
assert.equal(url.protocol, 'https:');
assert.ok(url.hostname.endsWith('.vercel.app'));
const output = path.dirname(profile);
const port = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0];
const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json());
const target = targets.find(item => item.type === 'page');
const socket = new WebSocket(target.webSocketDebuggerUrl);
await once(socket, 'open');
const pending = new Map();
const requests = [];
const responses = [];
const exceptions = [];
let sequence = 0;
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.id) {
    const task = pending.get(message.id);
    if (!task) return;
    pending.delete(message.id);
    clearTimeout(task.timer);
    if (message.error) task.reject(new Error(message.error.message));
    else task.resolve(message.result);
  }
  if (message.method === 'Network.requestWillBeSent') requests.push({ method: message.params.request.method, url: message.params.request.url });
  if (message.method === 'Network.responseReceived') responses.push({ url: message.params.response.url, status: message.params.response.status, mimeType: message.params.response.mimeType });
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
});

function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Browser command timed out: ${method}`)); }, 120_000);
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
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error(`Browser condition timed out: ${expression}`);
}

async function click(selectorExpression) {
  const point = await evaluate(`(() => { const element = ${selectorExpression}; if (!element || element.disabled) throw new Error('Control unavailable'); element.scrollIntoView({block:'center',behavior:'instant'}); const rectangle = element.getBoundingClientRect(); return {x:rectangle.x+rectangle.width/2,y:rectangle.y+rectangle.height/2}; })()`);
  await command('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 });
  await command('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 });
}

const button = label => `[...document.querySelectorAll('button')].find(element => element.textContent === ${JSON.stringify(label)})`;
const evidence = { schema: 'benchproof/vercel-browser-check-v1', url: url.origin, timestamp: new Date().toISOString(), freshProfile: true, verified: false };
try {
  await command('Page.enable');
  await command('Runtime.enable');
  await command('Network.enable');
  await command('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await command('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: output });
  await command('Page.navigate', { url: url.href });
  await waitFor("document.querySelectorAll('.example-card').length === 5 && /Worker\\s+alive/i.test(document.body.innerText)");
  assert.equal(await evaluate("document.querySelector('select').value"), 'live');
  await click("[...document.querySelectorAll('.example-card')].find(element => element.querySelector('strong')?.textContent === 'clean-service').querySelector('button')");
  await waitFor("document.querySelector('#run-h')?.textContent.includes('clean-service') && ![...document.querySelectorAll('button')].find(element => element.textContent === 'Verify independently')?.disabled");
  const auditId = await evaluate("localStorage.getItem('benchproof.active-audit')");
  assert.match(auditId, /^audit-/);
  await click(button('Verify independently'));
  await waitFor("document.querySelector('.gate-result')?.textContent.includes('VERIFIED') || [...document.querySelectorAll('.run-panel strong')].some(element => element.textContent === 'VERIFIED')");
  await waitFor(`${button('Build bundle')}?.disabled === false`);
  await click(button('Build bundle'));
  await waitFor("!!document.querySelector('.evidence-card')");
  await waitFor(`${button('Validate hashes')}?.disabled === false`);
  await click(button('Validate hashes'));
  await waitFor("document.body.innerText.includes('INTEGRITY PASS')");
  await waitFor(`${button('Replay checks')}?.disabled === false`);
  await click(button('Replay checks'));
  await waitFor("document.body.innerText.includes('replay matches the recorded checks')");
  await waitFor(`${button('Download authenticated ZIP')}?.disabled === false`);
  await click(button('Download authenticated ZIP'));
  const filename = `benchproof-audit-${auditId}.zip`;
  const deadline = Date.now() + 30_000;
  while (!(await readdir(output)).includes(filename) && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 500));
  const bytes = await readFile(path.join(output, filename));
  const metadata = await evaluate(`fetch('/api/v1/audits/${auditId}/bundle?metadata=true',{headers:{'X-BenchProof-Owner':localStorage.getItem('benchproof.owner-capability')}}).then(response=>response.json())`);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), metadata.sha256);
  assert.ok(await evaluate("document.querySelectorAll('.event-log li').length > 0"));
  const cursor = await evaluate(`Number(localStorage.getItem('benchproof.cursor.${auditId}'))`);
  assert.ok(cursor > 0);
  const screenshot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await writeFile(path.join(output, 'verified-journey.png'), Buffer.from(screenshot.data, 'base64'));
  const layouts = [];
  for (const width of [1440, 768, 390, 320]) {
    await command('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: width < 600 });
    await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
    const layout = await evaluate(`(() => {
      const overflow = [...document.querySelectorAll('.panel, .btn, .card, .verdict-grid, .next-action')].filter(element => {
        const rectangle = element.getBoundingClientRect();
        return rectangle.width && (rectangle.left < -1 || rectangle.right > innerWidth + 1);
      }).map(element => element.className);
      return {width: innerWidth, documentWidth: document.documentElement.scrollWidth, overflow};
    })()`);
    assert.ok(layout.documentWidth <= width + 1, `Active audit page overflows at ${width}px`);
    assert.deepEqual(layout.overflow, [], `Active audit controls overflow at ${width}px`);
    layouts.push(layout);
    if (width === 390) {
      await evaluate('scrollTo(0, 0)');
      const mobile = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
      await writeFile(path.join(output, 'verified-journey-mobile.png'), Buffer.from(mobile.data, 'base64'));
    }
  }
  evidence.layouts = layouts;
  await command('Page.reload', { ignoreCache: true });
  await waitFor(`document.querySelector('#run-h')?.textContent.includes('${auditId}') && [...document.querySelectorAll('.run-panel strong')].some(element => element.textContent === 'VERIFIED')`);
  assert.ok(await evaluate(`Number(localStorage.getItem('benchproof.cursor.${auditId}')) >= ${cursor}`));
  assert.equal(requests.filter(item => item.method === 'POST' && new URL(item.url).pathname === '/api/v1/audits').length, 1);
  assert.ok(responses.some(item => item.mimeType === 'text/event-stream'));
  assert.deepEqual(exceptions, []);
  assert.ok(responses.every(item => item.status < 400));
  Object.assign(evidence, { auditId, liveModeDefault: true, gate: 'VERIFIED', bundleSha256: metadata.sha256, validation: true, replay: true, download: true, sse: true, reloadRestored: true, duplicateCreates: 0, exceptions, verified: true });
} catch (error) {
  evidence.failure = error.message;
  evidence.exceptions = exceptions;
  evidence.failedResponses = responses.filter(item => item.status >= 400);
  process.exitCode = 1;
} finally {
  await mkdir(output, { recursive: true });
  const record = path.join(output, `browser-check-${Date.now()}.json`);
  evidence.record = record;
  await writeFile(record, JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  await command('Browser.close').catch(() => {});
  socket.close();
}
