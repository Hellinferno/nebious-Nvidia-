# Windows and VS Code setup

Ravi has previously reported Windows, VS Code, Python 3.12.10, Node 24.12.0, and Git 2.51.2. Those reports are useful starting context; verify the actual environment for this project.

## Day 0 — checks that work without application code

Open a PowerShell terminal in VS Code and run:

```powershell
py -3.12 --version
node --version
npm --version
git --version
```

Record the results. If `py` is unavailable but Python 3.12 is installed, use its full executable path or `python` after checking its version. Keep the chosen command consistent.

Extract this pack into the future `BenchProof` repository. Do not overwrite a different project's README or credentials. Confirm which directory VS Code opened before initializing Git.

## Day 1 — repository scaffolding tasks

- [ ] Initialize the BenchProof source repository after inspecting any existing files.
- [ ] Create the source paths in [repository structure](05_REPOSITORY_STRUCTURE.md).
- [ ] Create `backend/pyproject.toml` and a dependency lock. Candidate libraries: FastAPI, Uvicorn, Pydantic, HTTPX, the OpenAI-compatible client, pytest, and the verified Contree packages. Python AST, Decimal, hashlib and sqlite3 support the initial graph/amount/state work without a separate graph database.
- [ ] Scaffold a React/TypeScript/Vite frontend; commit `package-lock.json`.
- [ ] Add `.env.example` and `.gitignore` before adding a real API key.
- [ ] Record the dependency versions that actually install and pass preflight. Do not pin invented versions in advance.

## Target local startup after scaffolding

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
Copy-Item .env.example .env
```

The editable install requires the planned backend package and dev extra to exist. The release setup must use the implemented lockfile workflow, not rely on unbounded latest package resolution.

In three separate terminals, after implementation:

```powershell
.\.venv\Scripts\python.exe -m uvicorn benchproof.api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
.\.venv\Scripts\python.exe scripts/start_worker.py
```

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Prefer these direct virtual-environment commands if script activation is blocked. Do not weaken global PowerShell policy merely to activate a virtual environment.

## Target environment variables

| Variable | Meaning | Treatment |
| --- | --- | --- |
| `NEBIUS_API_KEY` | Token Factory inference credential | Server-side secret |
| `NEBIUS_BASE_URL` | `https://api.tokenfactory.nebius.com/v1/` | Allowlisted server configuration |
| `NEBIUS_MODEL_ID` | Exact successfully tested NVIDIA model identifier | Copy from account model catalog; no guessed slug |
| `BENCHPROOF_RUNNER` | `contree`, explicitly tested alternate, or `mock` | Required mode |
| `CONTREE_BASE_URL` | Verified sandbox API URL | Provider configuration, not a user-input URL |
| `CONTREE_PROJECT_ID` | Actual project identifier if transport requires it | Record authentication requirements |
| `CONTREE_API_KEY` | Credential used by the sandbox transport | Server-side secret; may differ from inference key |
| `BENCHPROOF_DATA_DIR` | Persistent database/artifact parent | Local path, outside repository source |
| `BENCHPROOF_PUBLIC_MODE` | Restrict intake to curated examples | True for public release |
| `BENCHPROOF_MAX_AUDIT_SECONDS` | Initial target 300 | Validated resource ceiling |
| `BENCHPROOF_MAX_MODEL_CALLS` | Initial target 12 | Validated action ceiling |
| `BENCHPROOF_MAX_EXECUTIONS` | Initial target 12 | Includes baseline, final checks and mutant executions |
| `BENCHPROOF_MAX_PARALLEL_BRANCHES` | Initial target 2 | Worker/provider ceiling |
| `BENCHPROOF_MAX_AUDIT_USD` | Configure after measured pricing | Cost reservation and hard stop |
| `BENCHPROOF_ALLOWED_ORIGINS` | Exact local/hosted UI origins | No wildcard credentialed CORS |

Frontend configuration includes only the API origin if necessary. Never create `VITE_NEBIUS_API_KEY` or another public build variable containing a credential.

## Local execution policy

The API runs locally; audited code does not run in Ravi's normal shell. A local Docker adapter, if implemented, is for owned curated fixture development on an appropriate isolated machine. Windows/WSL availability is not assumed. Real final evidence requires the recorded live backend and real inference.

## Preflight acceptance

The health endpoint is reachable, the worker heartbeat is visible, a real inference succeeds, a bounded isolated command returns its exit code and artifact, and the UI labels the actual mode. Missing credentials must fail preflight rather than silently switching to a mock.

Troubleshooting order: verify directory → versions → locked installation → environment loading → account access → provider capabilities → app state. Save sanitized error details in the feedback log.

## Assurance-runtime setup additions

Create the accepted constraint registry, AST/manifest state builder, trusted oracle/check package and protected candidate launcher before advertising graph-backed verification. The candidate snapshot includes approved `app/` code only; hidden truth and evaluator assets stay outside it. Remove ML library dependencies unless a later documented feature actually needs them.

Add validated configuration for `BENCHPROOF_MAX_PATCH_ATTEMPTS=2`, `BENCHPROOF_MAX_MUTANTS=3`, `BENCHPROOF_MAX_CONTEXT_TOKENS=16000` and `BENCHPROOF_MAX_OUTPUT_TOKENS=2000` as initial targets. Every action remains subject to total time/call/execution/cost limits. Configure graph/fingerprint/evaluator versions in server-owned release metadata, not public user inputs.

Preflight now also verifies a pinned constraint/check mapping, source/contract hash mismatch rejection, a graph with visible coverage, an invalid candidate rejected by the protected gate, and a clean candidate accepted without an unnecessary repair. Rich ledger/recovery/mutation features are P1; mark them absent until tested. Commands remain targets until the source scripts exist.
