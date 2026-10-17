# Optional laptop-hosted fallback

The primary verified cloud demo is [benchproof.vercel.app](https://benchproof.vercel.app).
It runs independently of the laptop; see [Vercel operations](VERCEL_DEPLOYMENT.md).
This document retains the earlier laptop/ngrok fallback and its historical evidence.

Verified on 16 October 2026 using the existing authenticated ngrok installation:

https://dierdre-miasmatical-madge.ngrok-free.dev

Visitors on ngrok's free plan may need to click **Visit Site** once. The app runs
on the owner's laptop, so access depends on that laptop staying awake, connected,
and running Docker, the demo server and ngrok. This is a working demo URL, not
evidence of unattended availability throughout judging.

## Start or restart

Follow README setup first. Use separate PowerShell terminals from this repository.

```powershell
# Build the production UI. Its default API URL is now the same origin.
npm --prefix frontend run build

# Start the API, built UI, and a paired heartbeat process.
Set-Location backend
.\venv\Scripts\python.exe scripts\serve_demo.py --port 8765 --daily-actions 60
```

```powershell
# A second terminal; uses the already configured ngrok account.
ngrok http 8765
```

The server binds only to `127.0.0.1`. Port 8080 is reserved by Windows on the
verified machine; 8765 was tested successfully. Stop the server and tunnel with
Ctrl+C in their terminals. Do not stop unrelated Python or ngrok processes.

If using a fresh ngrok account, complete its authentication locally following
the [official setup guide](https://ngrok.com/docs/getting-started/). Do not commit
an ngrok token or paste it into a public issue. No owned domain is required for
the account-assigned development domain.

## Data and resource limits

- `artifacts/public-demo/benchproof.db`: separate persistent demo audit state.
- `artifacts/public-demo/limits.db`: shared daily action counter, using UTC days.
- `backend/artifacts/bundles/`: API-generated evidence exports.
- One changing or executing action at a time across visitors; concurrent actions
  receive `429 DEMO_BUSY`. The legacy GET replay route also consumes the limit.
- A shared limit of 60 actions per UTC day survives server restarts. Reads and
  cancellation remain available after the limit. Rejected requests also consume
  an action, so this is a protective ceiling rather than a billing counter.
- Existing audit/model/execution budgets remain in force. Each candidate runs
  with a 256 MB memory cap, one CPU, no network, and a fresh read-only source mount.
- The NVIDIA model runs remotely using the configured Nebius Token Factory key.
  No local model weights or GPU are needed.

These controls limit a small public demonstration; the opaque owner capability
is still the local/demo ownership boundary, not production account authentication.
The heartbeat helper reports liveness; it does not process queued background jobs.
There is no Windows service or automatic restart policy installed.

Only `frontend/dist` is served as static content. The repository root, `.env`,
databases and hidden evaluator assets are outside that static directory. Build
only with non-secret `VITE_*` variables; provider credentials stay server-side.

## Observed public checks

Public audit `audit-d8b7bb64b64f` exercised the clean service through HTTPS:
gate `VERIFIED`, bundle integrity valid, fresh Docker replay `VERIFIED` with all
checks matching, SSE event frames received, other-owner request `403`, and
`/.env` request `404`. Bundle SHA-256:
`05941a04cd223a37e37d5c931b1edcfd6dde17f9ec70f78d9c9fb1cc9ed1582b`.
This clean gate/replay test made no model call. The live development trial outcomes
and their failures are recorded separately in the README and progress log.

## Why this route

The owner's Azure subscription expired. Cloudflare Containers requires a paid
Workers plan, and free Workers cannot run the current Docker execution adapter.
Cloudflare Quick Tunnels provide a domain-free URL but do not support SSE, which
this UI uses. A named Cloudflare Tunnel requires a domain on Cloudflare.
Ngrok provides an account-assigned domain, and SSE was tested on this actual URL.

Provider limits checked on 16 October:

- [ngrok free limits](https://ngrok.com/docs/pricing-limits/free-plan-limits/):
  usage quotas and a browser warning apply; check account usage before judging.
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/):
  temporary hostname, no uptime guarantee, no SSE.
- [Cloudflare Tunnel prerequisites](https://developers.cloudflare.com/tunnel/get-started/):
  account, domain and a running origin server.
- [Cloudflare Containers pricing](https://developers.cloudflare.com/containers/platform/pricing/):
  paid Workers plan required.

Token Factory credits fund inference; they do not establish a separate AI Cloud
VM allocation or Sandboxes spawn entitlement. The local preflight still reports
no Nebius Sandboxes spawn/list permission.

## Still required before submission

Verify a fresh incognito browser journey, backup and restore both database and
artifact state, demonstrate restart/recovery, track ngrok quota and inference
credit expiry, and establish access for the entire judging period. Preserve
failed trials. Final held-out B0/B1/B2 trials, three successful live rehearsals,
clean-clone setup, final model/image notices, video and actual entry submission
remain open. No cloud VM, paid plan or Azure resource was provisioned.
