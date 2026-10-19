import { createHash } from 'node:crypto';
import { lstat, readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const projectRoot = fileURLToPath(new URL('../../', import.meta.url));
const roots = [
  'backend/benchproof',
  'backend/fixtures/development',
  'backend/runner',
  'frontend/dist',
];
const files = [
  'backend/requirements.lock.txt',
  'backend/scripts/start_worker.py',
  'backend/scripts/serve_demo.py',
  'backend/scripts/runner_preflight.py',
  'deployment/vercel/origin.py',
  'deployment/vercel/bootstrap.sh',
];

export function allowedFile(filename) {
  if (filename.includes('\\') || filename.split('/').some(part => part === '..' || part.startsWith('.'))) return false;
  if (filename.includes('__pycache__') || filename.endsWith('.pyc')) return false;
  if (files.includes(filename)) return true;
  if (filename.startsWith('backend/benchproof/')) return filename.endsWith('.py');
  if (filename.startsWith('backend/fixtures/development/')) return /\.(py|json)$/.test(filename);
  if (filename.startsWith('backend/runner/')) return filename.endsWith('.py') || filename === 'backend/runner/image/Dockerfile';
  return filename.startsWith('frontend/dist/') && /\.(html|js|css|svg|png|ico|woff2?)$/.test(filename);
}

export async function makePackage(root = projectRoot) {
  const names = new Set(files);
  async function visit(relative) {
    const absolute = path.join(root, relative);
    const stat = await lstat(absolute);
    if (stat.isSymbolicLink()) throw new Error(`Symlinks are refused: ${relative}`);
    if (stat.isDirectory()) {
      for (const item of await readdir(absolute)) {
        if (item.startsWith('.') || item === '__pycache__') continue;
        await visit(`${relative}/${item}`);
      }
    } else if (allowedFile(relative)) names.add(relative);
  }
  for (const relative of roots) await visit(relative);
  const entries = [];
  for (const name of [...names].sort()) {
    if (!allowedFile(name)) throw new Error(`Forbidden runtime file: ${name}`);
    const stat = await lstat(path.join(root, name));
    if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`Not a regular file: ${name}`);
    const bytes = await readFile(path.join(root, name));
    if (bytes.length > 2 * 1024 * 1024) throw new Error(`Runtime file too large: ${name}`);
    if ((name.endsWith('.sh') || name.endsWith('/Dockerfile')) && bytes.includes(13)) {
      throw new Error(`CRLF line endings are refused in Linux-executed file: ${name}`);
    }
    entries.push({ path: name, sha256: createHash('sha256').update(bytes).digest('hex'), content: bytes.toString('base64') });
  }
  const hash = createHash('sha256').update(JSON.stringify(entries.map(({ path: name, sha256 }) => [name, sha256]))).digest('hex');
  return { schema: 'benchproof/vercel-runtime-v1', hash, entries };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const runtime = await makePackage();
  await writeFile(new URL('./runtime-package.json', import.meta.url), JSON.stringify(runtime));
  console.log(`Runtime package ${runtime.hash}: ${runtime.entries.length} allowlisted files; no holdout or local state`);
}
