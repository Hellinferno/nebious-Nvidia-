# BenchProof — Submission & Clean-Clone Verification Checklist (C-10)

## 1. Project & Hackathon Metadata

- **Track**: Coding and Agentic Engineering
- **Project Name**: BenchProof
- **Tagline**: Autonomous coding agent and engineering assurance runtime with isolated test execution and guarded task revision.
- **Public Demo**: [https://benchproof.vercel.app](https://benchproof.vercel.app)
- **License**: Apache 2.0 (see [LICENSE](LICENSE) and [NOTICE](NOTICE))
- **Release Evidence**: [VERIFICATION.md](VERIFICATION.md); verify `git rev-parse HEAD` and a clean tree at publication, not merely from this checklist.

---

## 2. Clean-Clone Setup & Reproduction Guide

### Prerequisites
- Python 3.12+ (tested with 3.12.10)
- Node.js 24.x (tested with 24.12.0) & npm 11+
- Git
- Docker is required for real candidate execution (local Docker or the dedicated cloud runner); mock mode is exploration-only.

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
# Selected no-inference/no-candidate regressions
cd backend
python -m pytest tests/test_release_admission.py tests/test_coding_store.py tests/test_coding_api.py

# Run C-08 Cloud Failure Mode Acceptance Suite
python -m pytest tests/test_cloud_acceptance.py -v

# The full suite includes fixture execution: run it only in an isolated test container.
# Scripted evaluation also requires Docker and is not a live-model benchmark.
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

# Terminal 2 — Coding worker (only after configuring approved budgets/deadline)
cd backend
python scripts/start_worker.py

# Terminal 3 — Frontend UI
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

The copied environment defaults to no-spend mock mode. Follow **Enable live coding
deliberately** in the root README before enabling real plans/execution. API and worker
must share the same root environment/database. The no-spend setup was verified on
21 October in an independent clone of `7b7349a`, including locked dependency
installation, API/worker/UI startup and real desktop/mobile browser checks. No
candidate code or inference ran on the laptop. Real isolated execution is separately
verified in the cloud runtime, not inferred from the clone smoke. See [VERIFICATION.md](VERIFICATION.md).

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
| **C-10** | Clean-clone, rights/attribution, video and owner submission | 26–28 Oct | **PARTIAL** | No-spend clean-clone startup/browser and corrected media checks pass; owner final video/rights review and submitted-status evidence remain |

---

## 4. Existing Video Recording Walkthrough (<= 3 Minutes)

The 21 October correction replaces the actual MP4 narration and embedded/standalone
subtitles, removes the incorrect signed-ZIP claim and adds a dated current-release
rehearsal still. The main footage reviews a saved completed task: it is not a fresh
continuous live inference/approval/rollback recording. See [provenance](recordings/README.md).
Full decode and caption consistency pass; owner final viewing/rights approval remains.

- **File Path**: [`recordings/benchproof_demo_walkthrough.mp4`](recordings/benchproof_demo_walkthrough.mp4)
- **Duration**: **02:18.28** (138.28 seconds), below three minutes; owner must confirm final event requirements.
- **Resolution**: 1280x720 (720p HD @ 25 fps, H.264/AVC)
- **Audio**: AAC 192kbps stereo with Microsoft David narrative voiceover
- **Subtitles**: Embedded timed subtitle track (`mov_text`) + standalone [`recordings/subtitles.srt`](recordings/subtitles.srt)
- **Production URL Demonstrated**: `https://benchproof.vercel.app`
- **Methodology**: Browser footage reviewing saved production task evidence, locally synthesized narration and one dated still from the separate two-call customized rehearsal; not a user study or continuous new live run.

| Time Window | Scene / Screen | Narrative Key Points | Verified Visual Artifact |
|---|---|---|---|
| **0:00 – 0:25** | Overview | Guarded workflow and explicit saved-task-review disclosure. | [`frame_scene1.png`](recordings/frame_scene1.png) |
| **0:25 – 0:46** | Intake boundaries | StringCalculator, editable `app/` vs protected imported `tests/`. | [`frame_scene2.png`](recordings/frame_scene2.png) |
| **0:46 – 1:04** | Saved plan review | Recorded model plan and approval/source binding; not a new approval. | [`frame_scene3.png`](recordings/frame_scene3.png) |
| **1:04 – 1:27** | Recorded test results | Failing baseline, passing candidate/final checks and scoped REVIEW_READY. | [`frame_scene4.png`](recordings/frame_scene4.png) |
| **1:27 – 1:44** | Diff and checkpoint controls | Exact patch and saved revision controls; no newly executed rollback claimed. | [`frame_scene5.png`](recordings/frame_scene5.png) |
| **1:44 – 2:03** | Export | Diff, plan, checks and trace; ZIP explicitly not digitally signed. | [`frame_scene6.png`](recordings/frame_scene6.png) |
| **2:03 – 2:18** | Dated 21 October still | Separate customized rehearsal: skill, harness, MCP snapshot, two model calls and three isolated executions. | [`frame_scene7.png`](recordings/frame_scene7.png) |

---

## 5. Factual Devpost Submission Text

### Project Title
BenchProof: Autonomous Coding Agent & Engineering Assurance Runtime

### Tagline
Task-centered coding agent with human-approved plans, isolated candidate test execution, bounded multi-turn revision, and verifiable diff review.

### Inspiration
Plausible edits still need testing and review, and unattended retries can consume resources without useful progress. We built BenchProof around a guarded coding workflow: approved plans, immutable imported tests, isolated execution, bounded retries and reviewable checkpoints. These safeguards are design choices, not evidence of superiority over other assistants.

### What It Does
1. **Constrained Project Intake**: Safely ingests Python projects with path-traversal prevention, file size enforcement, secret screening, and manifest fingerprinting.
2. **Human-in-the-Loop Plan Review**: The agent inspects the code, produces a step-by-step implementation plan, and waits for explicit user approval before mutating any file.
3. **Protected Test Boundaries**: Test files (`tests/`) are strictly protected from modification, preventing the agent from "fixing" bugs by weakening assertions.
4. **Isolated Candidate Execution**: Candidate code executes in an isolated Docker container with network denied, timeouts, and resource limits; no host-process fallback is used for real tasks.
5. **Bounded Multi-Turn Revision**: Test failures provide real compiler and test feedback to the model for bounded revision attempts, with automatic repeated-candidate stall detection.
6. **Compare-and-Swap Checkpoint Rollback**: Every state mutation is checkpointed; users can rollback to any prior checkpoint without resetting consumed resource budgets.
7. **Reviewable Export Bundles**: Exports unified diffs, recorded checks, plans and event traces. Source/plan hashes bind recorded versions; archives are not digitally signed or proof of every requirement.
8. **Bounded Customization**: Browser-local profiles, instruction-only skills, two reviewed harness policies and a consented read-only documentation MCP snapshot. Arbitrary executable plugins and unrestricted MCP tools are not supported.

### How We Built It
- **Inference**: NVIDIA Nemotron models hosted on Nebius Token Factory for planning, diagnosis, and code generation.
- **Backend**: FastAPI, Python 3.12, SQLite with WAL checkpointing, Pydantic v2 schemas, and isolated Docker candidate execution.
- **Frontend**: React 19, TypeScript, Vite, with custom unified diff viewer, test terminal console, 8-stage execution stepper, and budget gauges.
- **Assurance**: Six frozen scripted gold-answer regressions, cloud failure-mode tests and version-linked evidence exports; not a held-out live-model benchmark.

### Challenges We Overcame
- Preventing candidate loops from wasting inference quota when generating duplicate edits.
- Enforcing monotonic worker fencing tokens to recover from cloud worker crashes without double-execution.
- Keeping trusted evaluator assets out of candidates and screening exports; do not put credentials in user instructions or reference context.

### Accomplishments We're Proud Of
- Current deployed release: 631 backend, three separate Docker integration cases, 29 frontend and 23 deployment/toolchain tests pass. Real public acceptance and a customized two-call live model task pass, including desktop/mobile export and reload. See `VERIFICATION.md` and `RELEASE_REHEARSAL.md` for scope and remaining gates.
- Six scripted gold-answer regressions passed historically. Their responses and token usage are synthetic, not a live-model benchmark or holdout success rate.
- Responsive React workspace with passing lint/build and checked desktop/mobile layouts.
- Real end-to-end NVIDIA Nemotron-3-Nano-30B-A3B inference on Nebius Token Factory with isolated candidate Docker verification live on production.

### What We Learned
Passing supplied checks is useful but does not prove every requirement. Explicit approval, resource limits, recorded failures and reviewable diffs make the workflow inspectable; their effect on model error rates still requires a fair evaluation.

### What's Next
- Extended multi-language support (TypeScript, Go, Rust).
- Git repository branch integration with automatic pull request generation.
- Scaled parallel evaluation worker pools for large test suites.
