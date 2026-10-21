# Deployment dependency review — 21 October 2026

This is a scoped npm advisory remediation, not a full security certification.
The production `@vercel/sandbox` dependency stays at 3.8.0; frontend runtime
dependencies are unchanged. No forced major upgrade or automatic audit fix was applied.

## Reviewed deployed changes

- Vercel CLI 64.3.1 → 64.7.0, within the existing major release.
- Fresh clean-clone installation additionally exposed a Vite development-server
  advisory missed by the earlier frontend audit. Vite 8.3.2 → pinned 8.3.3 fixes
  that compatible patch path. The [maintainer release](https://github.com/vitejs/vite/releases/tag/v8.3.3)
  updates launch-editor to 2.14.2; npm registry integrity and the lockfile are checked.
  The patched frontend audit reports zero; 29 frontend and 23 deployment/toolchain
  cases, lint/build pass. The build reproduces the exact deployed runtime hash,
  so no runtime replacement or repeated inference was needed. Do not expose the
  development server beyond loopback or treat the scoped audit as certification.
- Root overrides apply only below the Vercel development dependency: ajv 8.20.0,
  js-yaml 4.3.2, minimatch 10.2.6, path-to-regexp 6.3.0/8.4.2, smol-toml 1.9.1,
  tar 7.5.22, and undici 5.29.0. Existing dependency major versions are preserved.
- Package versions were checked against the official npm registry. Version-scoped
  nested overrides follow the [npm package configuration reference](https://docs.npmjs.com/cli/v11/configuring-npm/package-json/#overrides).
- Installation uses the lockfile with lifecycle scripts disabled. Gateway/runtime
  tests, a lockfile regression, frontend lint/build and CLI version startup are
  checked separately. This does not test every framework builder embedded in CLI.
- The first actual Linux deployment rejected the Windows-generated lockfile because
  optional peers `@emnapi/core` and `@emnapi/runtime` 1.11.3 were missing. Their
  registry-verified entries are now locked and covered by the toolchain regression.
  The subsequent Linux `npm ci`, frontend install/build and production deployment
  pass. The failed deployment is retained as `dpl_6dmZjEdYRXbBvbGT6faLUv4QtWnD`;
  the successful deployment is `dpl_7SPDgfYC3M5HLPCThyCMWEPBRgi7`.

## Remaining risk

The initial root audit reported 33 advisories (one critical, 24 high, eight moderate).
After compatible patches it reports **23 high, zero critical and zero moderate**;
the root production-only audit reports **zero**. Counts include transitive packages
affected by the same underlying advisory and must not be treated as independent
application exploits. Saved reports are in `artifacts/release-hardening-20261020/`.

Remaining underlying paths include undici 5.x, @fastify/busboy 2.x and braces 3.x
inside the Vercel development toolchain. Updating undici to 5.29.0 removes its older
patchable issues but not advisories requiring a newer major. No patched compatible
braces 3.x version was available in the queried registry. Busboy/undici major
replacement must not be forced merely to make the audit count zero: upstream
consumers and CLI authentication/deployment paths require compatibility validation.

Do not process untrusted archives, build arbitrary third-party repositories or
install user projects through this development CLI. BenchProof's public candidate
runner does not mount node_modules or run the CLI inside candidate containers.
Keep using the reviewed build inputs and existing isolated Python runner. An
upstream CLI fix or separately validated dependency/toolchain migration remains
open in R-03. Fresh audits are required before the next release; a zero production
npm count says nothing about Python dependencies or all application vulnerabilities.
