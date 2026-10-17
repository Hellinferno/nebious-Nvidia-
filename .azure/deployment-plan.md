# Azure Deployment Plan

## Status

Blocked — Azure subscription expired (reported by the owner on 16 October 2026).

## Objective

Deploy the exact BenchProof release with HTTPS, persistent state and artifacts, a supervised worker, server-side Nebius credentials, and the validated isolated candidate runner.

## Current Decisions

- Application mode: existing application modification.
- Subscription: unavailable; do not provision Azure resources.
- Region and Azure deployment recipe: not selected because the subscription expired.
- Resource names, cost controls, persistence, backup, and rollback: pending planning.

## Planned Work

- [ ] Analyze application components and deployment requirements.
- [ ] Select the Azure architecture and infrastructure recipe.
- [ ] Confirm subscription, region, resource naming, and cost constraints.
- [ ] Generate application packaging and infrastructure artifacts.
- [ ] Validate security, persistence, recovery, and local behavior.
- [ ] Run Azure validation before deployment.
- [ ] Deploy and verify the public release.

## Blocking Decisions

- Azure is excluded from the current deployment path. No Azure resources were created.
- An available Linux host or Nebius AI Cloud compute account is required for a replacement deployment.
- Token Factory inference remains operational. Token Factory inference access does not establish AI Cloud compute or Sandboxes spawn access.
- Local Docker isolation was verified on 16 October; local operation does not establish a persistent public judging URL.
