# BenchProof — Submission & Clean-Clone Verification Checklist (C-10)

## 1. Project & Hackathon Metadata

- **Track**: Coding and Agentic Engineering
- **Project Name**: BenchProof
- **Tagline**: Autonomous coding agent and engineering assurance runtime with isolated test execution and guarded task revision.
- **Public Demo**: [https://benchproof.vercel.app](https://benchproof.vercel.app)
- **License**: Apache 2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE))
- **Head Repository Commit**: Verified clean tree on active branch

---

## 2. Clean-Clone Setup & Reproduction Guide

### Prerequisites
- Python 3.12+ (tested with 3.12.10)
- Node.js 20+ (tested with 24.12.0) & npm 10+
- Git
- Optional: Docker Desktop (for isolated container runner)

### Step 1: Clone Repository
```bash
git clone https://github.com/Hellinferno/nebious-Nvidia-.git benchproof
cd benchproof
```

### Step 2: Backend Setup
```powershell
# Create Python 3.12 virtual environment
py -3.12 -m venv backend/venv

# Activate environment (PowerShell)
.\backend\venv\Scripts\Activate.ps1

# Install pinned dependencies
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.lock.txt
python -m pip install -e ".\backend[dev]" --no-deps

# Configure environment variables
Copy-Item .env.example .env
# Set NEBIUS_API_KEY in .env if executing live NVIDIA Token Factory calls
```

### Step 3: Frontend Setup
```bash
cd frontend
npm ci
cd ..
```

### Step 4: Run Automated Verification Tests
```powershell
# Run the complete backend test suite (Docker integration requires a working daemon)
cd backend
python -m pytest

# Run C-08 Cloud Failure Mode Acceptance Suite
python -m pytest tests/test_cloud_acceptance.py -v

# Run C-09 Frozen Evaluation Suite
python -m pytest tests/test_coding_evaluation.py -v
cd ..

# Run frontend tests and linter
cd frontend
npm test
npm run lint
cd ..
```

### Step 5: Run Evaluation Rehearsal Harness
```powershell
# Executes the 6 frozen benchmark tasks and produces JSON/Markdown reports
cd backend
python scripts/run_coding_eval.py --scripted-smoke
cd ..
# Inspect generated report in artifacts/rehearsals/
```

### Step 6: Verify Database Backup & Restore
```powershell
cd backend
# Create WAL-consistent snapshot
python scripts/backup_restore.py backup --db-path benchproof.db --backup-dir ./backups

# Verify / Restore snapshot
python scripts/backup_restore.py restore --manifest ./backups/<backup_folder>/manifest.json --target-db ./restored.db
cd ..
```

### Step 7: Launch Local Application
```powershell
# Terminal 1 — Backend API
cd backend
python -m uvicorn benchproof.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend UI
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

---

## 3. Milestones C-01 to C-10 Status

| Milestone | Description | Target | Status | Verification Reference |
|---|---|---|---|---|
| **C-01** | Diagnosis, output truncation handling, and bounded generation | 17 Oct | **DONE** | `artifacts/coding/c01-live-20261017-1/` |
| **C-02** | Versioned contracts, durable store, leased worker, admission limits | 17–18 Oct | **DONE** | `backend/benchproof/coding/store.py`, `worker.py` |
| **C-03** | End-to-end coding loop, revision feedback, repeated-candidate stall | 18 Oct | **DONE** | `backend/scripts/run_coding_loop.py` |
| **C-04** | Project intake limits, manifest fingerprints, isolated runner | 19–20 Oct | **DONE** | `backend/benchproof/intake/`, `backend/runner/` |
| **C-05** | Real bug fix & feature on imported projects, protected test refusal | 20–21 Oct | **DONE** | `backend/tests/test_project_tasks.py` |
| **C-06** | Checkpoint log, CAS restore, pause/resume/cancel, sanitized bundle | 21–22 Oct | **DONE** | `backend/tests/test_coding_checkpoints.py` |
| **C-07** | Primary Task Workspace UI, diff viewer, test terminal, export | 22–23 Oct | **DONE** | `frontend/src/components/coding/CodingWorkspace.tsx` |
| **C-08** | Cloud acceptance, lease recovery, quotas, backup/restore | 23–24 Oct | **DONE** | `backend/tests/test_cloud_acceptance.py` (7/7 pass) |
| **C-09** | Versioned task suite and regression harness | 24–26 Oct | **PARTIAL** | Six scripted gold-answer tasks; held-out live-model benchmark remains open |
| **C-10** | Clean-clone, rights/attribution, video storyboard, submission prep | 26–28 Oct | **DONE** | `SUBMISSION_CHECKLIST.md`, clean build & tests |

---

## 4. Video Recording Walkthrough (<= 3 Minutes) — COMPLETE

- **File Path**: [`recordings/benchproof_demo_walkthrough.mp4`](file:///d:/Nvidia%20hackathon/recordings/benchproof_demo_walkthrough.mp4)
- **Duration**: **02:03** (123.27 seconds) — strictly complies with the &le; 3 minutes (180s) competition limit.
- **Resolution**: 1280x720 (720p HD @ 25 fps, H.264/AVC)
- **Audio**: AAC 192kbps stereo with Microsoft David narrative voiceover
- **Subtitles**: Embedded timed subtitle track (`mov_text`) + standalone [`recordings/subtitles.srt`](file:///d:/Nvidia%20hackathon/recordings/subtitles.srt)
- **Production URL Demonstrated**: `https://benchproof.vercel.app`
- **Methodology**: Real browser screen recording using Playwright-Core + Google Chrome against live production, driven by NVIDIA Nemotron-3-Nano-30B-A3B inference on Nebius Token Factory.

| Time Window | Scene / Screen | Narrative Key Points | Verified Visual Artifact |
|---|---|---|---|
| **0:00 – 0:25** | Architecture overview & problem statement | LLMs often hallucinate repairs and overwrite test suites. BenchProof enforces guarded engineering, immutable manifests, and isolated execution. | [`frame_scene1.png`](file:///d:/Nvidia%20hackathon/recordings/frame_scene1.png) |
| **0:25 – 0:46** | Interactive Project Intake & Boundary Protection | Selecting StringCalculator. Editable `app/` files vs immutable, protected `tests/`. Crafting the negative number task brief. | [`frame_scene2.png`](file:///d:/Nvidia%20hackathon/recordings/frame_scene2.png) |
| **0:46 – 1:04** | Cryptographic Planning & Human Approval | NVIDIA Nemotron multi-step plan generation. Immutable plan hash and explicit human approval before code mutation. | [`frame_scene3.png`](file:///d:/Nvidia%20hackathon/recordings/frame_scene3.png) |
| **1:04 – 1:27** | Stepper Execution & Isolated Test Runner | 8-stage stepper progress: Baseline failure -> Nemotron surgical edit -> Candidate re-test in container (network denied, limits enforced) -> REVIEW_READY. | [`frame_scene4.png`](file:///d:/Nvidia%20hackathon/recordings/frame_scene4.png) |
| **1:27 – 1:44** | Unified Diff Review & Checkpoint Rollback | Syntax-highlighted diff of `app/calculator.py`. Compare-and-swap (CAS) checkpoint timeline with instant rollback without budget reset. | [`frame_scene5.png`](file:///d:/Nvidia%20hackathon/recordings/frame_scene5.png) |
| **1:44 – 2:03** | Evidence Bundle Export & Live Deployment | Complete verifiable signed `.zip` export (diffs, test logs, event trace). Accessible live on production at `benchproof.vercel.app`. | [`frame_scene6.png`](file:///d:/Nvidia%20hackathon/recordings/frame_scene6.png) |

---

## 5. Factual Devpost Submission Text

### Project Title
BenchProof: Autonomous Coding Agent & Engineering Assurance Runtime

### Tagline
Task-centered coding agent with human-approved plans, isolated candidate test execution, bounded multi-turn revision, and verifiable diff review.

### Inspiration
Most AI coding assistants operate unconstrained: they suggest code that looks plausible but fails silently, overwrite test assertions to fake green results, or loop indefinitely when encountering runtime errors. We built BenchProof to solve this problem by treating code generation as a guarded engineering process with deterministic test isolation, protected test immutability, and auditable checkpoint rollbacks.

### What It Does
1. **Constrained Project Intake**: Safely ingests Python projects with path-traversal prevention, file size enforcement, secret screening, and manifest fingerprinting.
2. **Human-in-the-Loop Plan Review**: The agent inspects the code, produces a step-by-step implementation plan, and waits for explicit user approval before mutating any file.
3. **Protected Test Boundaries**: Test files (`tests/`) are strictly protected from modification, preventing the agent from "fixing" bugs by weakening assertions.
4. **Isolated Candidate Execution**: Candidate code executes in an isolated runner process or container with network denied, timeouts, and resource limits.
5. **Bounded Multi-Turn Revision**: Test failures provide real compiler and test feedback to the model for bounded revision attempts, with automatic repeated-candidate stall detection.
6. **Compare-and-Swap Checkpoint Rollback**: Every state mutation is checkpointed; users can rollback to any prior checkpoint without resetting consumed resource budgets.
7. **Verifiable Export Bundles**: Produces complete cryptographic evidence bundles containing unified diffs, test logs, plans, and event traces.

### How We Built It
- **Inference**: NVIDIA Nemotron models hosted on Nebius Token Factory for planning, diagnosis, and code generation.
- **Backend**: FastAPI, Python 3.12, SQLite with WAL checkpointing, Pydantic v2 schemas, and isolated child process/container test runners.
- **Frontend**: React 19, TypeScript, Vite, with custom unified diff viewer, test terminal console, 8-stage execution stepper, and budget gauges.
- **Assurance**: Automated evaluation suite with 6 frozen benchmark tasks, cloud failure mode acceptance suite, and cryptographic evidence exports.

### Challenges We Overcame
- Preventing candidate loops from wasting inference quota when generating duplicate edits.
- Enforcing monotonic worker fencing tokens to recover from cloud worker crashes without double-execution.
- Keeping trusted evaluator assets out of candidates and screening exports; do not put credentials in user instructions or reference context.

### Accomplishments We're Proud Of
- Current verification: 602 backend tests passed in isolated Linux Docker, three Docker integration cases passed separately, and 29 frontend tests passed. See `VERIFICATION.md` for scope and remaining release limits.
- Six scripted gold-answer regressions passed historically. Their responses and token usage are synthetic, not a live-model benchmark or holdout success rate.
- Fast, responsive React frontend building in under 300ms with zero lint warnings.
- Real end-to-end NVIDIA Nemotron-3-Nano-30B-A3B inference on Nebius Token Factory with isolated candidate Docker verification live on production.

### What We Learned
Deterministic test isolation combined with human-reviewed execution plans dramatically reduces model hallucinations and makes autonomous coding predictable and safe.

### What's Next
- Extended multi-language support (TypeScript, Go, Rust).
- Git repository branch integration with automatic pull request generation.
- Scaled parallel evaluation worker pools for large test suites.
