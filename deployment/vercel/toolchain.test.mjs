import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

test('deployment toolchain locks reviewed compatible patches without changing production dependencies', async () => {
  const manifest = JSON.parse(await readFile(new URL('../../package.json', import.meta.url), 'utf8'));
  const lock = JSON.parse(await readFile(new URL('../../package-lock.json', import.meta.url), 'utf8'));
  assert.equal(manifest.devDependencies.vercel, '64.7.0');
  assert.equal(lock.packages['node_modules/vercel'].version, manifest.devDependencies.vercel);
  assert.deepEqual(manifest.dependencies, { '@vercel/sandbox': '3.8.0' });
  assert.deepEqual(Object.keys(manifest.overrides), ['vercel']);
  for (const name of ['@emnapi/core', '@emnapi/runtime']) {
    const peer = lock.packages[`node_modules/${name}`];
    assert.equal(peer?.version, '1.11.3', `Missing cross-platform optional peer ${name}`);
    assert.equal(peer.dev, true);
    assert.equal(peer.optional, true);
    assert.match(peer.integrity, /^sha512-/);
  }
  const patches = {
    ajv: '8.20.0', 'js-yaml': '4.3.2', minimatch: '10.2.6',
    'path-to-regexp': '8.4.2', 'smol-toml': '1.9.1', tar: '7.5.22', undici: '5.29.0',
  };
  for (const [name, version] of Object.entries(patches)) {
    const packages = Object.entries(lock.packages).filter(([filename]) => filename.endsWith(`/node_modules/${name}`) || filename === `node_modules/${name}`);
    const major = version.split('.')[0];
    const matching = packages.filter(([, metadata]) => metadata.version?.split('.')[0] === major);
    assert.ok(matching.length > 0, `Missing patched ${name}`);
    for (const [, metadata] of matching) assert.equal(metadata.version, version, `${name} patch changed`);
  }
  for (const [filename, metadata] of Object.entries(lock.packages)) {
    if (filename.endsWith('/path-to-regexp') && metadata.version?.startsWith('6.')) assert.equal(metadata.version, '6.3.0');
  }
});
