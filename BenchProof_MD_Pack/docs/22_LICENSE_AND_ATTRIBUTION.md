# License, ownership, and attribution work

Status: Verified for C-10 release. First-party Apache-2.0 `LICENSE` and `NOTICE` confirmed at repository root. Third-party direct and transitive dependency licenses, container runtime images, synthetic benchmarks, and model API terms reviewed.

## First-party license

Original BenchProof source, synthetic fixtures and documentation use the standard Apache-2.0 text in top-level [LICENSE](../../LICENSE), with scope notes in [NOTICE](../../NOTICE). This follows the release plan; the earlier suggestion of MIT was not adopted.

Keep first-party code, fixture generation, UI assets, and original documentation distinct from third-party components. A permissive first-party license does not override dependencies' or model weights' terms.

## Inventory

| Component | Source/version | License or terms | How used | Required notices | Checked |
| --- | --- | --- | --- | --- | --- |
| First-party BenchProof code | Repository root | Apache-2.0 | Application | Top-level LICENSE/NOTICE | Verified |
| NVIDIA model inference | Nebius Token Factory (`nvidia/*`) | NVIDIA Open Model License / Nebius terms | Remote inference | Interoperability disclaimer in NOTICE | Verified |
| Python direct runtime packages | FastAPI 0.142.2, Pydantic 2.13.5, pydantic-settings 2.15.0 | MIT | Backend | Preserve package license | Verified |
| Python network/server packages | Uvicorn 0.54.0, HTTPX 0.28.1, python-dotenv 1.2.4 | BSD-3-Clause | Backend | Preserve package license | Verified |
| OpenAI Python client | Installed 3.24.0 | Apache-2.0 | Nebius-compatible API client | Preserve package license | Verified |
| JavaScript direct packages | React/react-dom 19.3.0, Axios 1.20.0, Vite 8.3.2, oxlint 1.86.0 | MIT | UI/build | Preserve package notices | Verified |
| TypeScript | Lockfile 6.0.3 | Apache-2.0 | UI type checking/build | Preserve package notices | Verified |
| Vercel Sandbox / CLI | `@vercel/sandbox` 3.8.0, Vercel CLI 64.3.1 | Apache-2.0 | Hosted cloud runner | Preserve package notices | Verified |
| Container base image | `python:3.12-slim` | PSF / Debian DFSG | Isolated runner | Included in runner Dockerfile | Verified |
| Synthetic tasks & fixtures | `StringCalculator`, `BankAccount`, `StockManager`, etc. | Apache-2.0 | Test benchmarks | First-party synthetic disclosure | Verified |
| Icons / UI media | First-party SVG | Apache-2.0 | UI rendering | First-party assets | Verified |

## Ownership checks

- [x] Ravi owns or has suitable rights to the first-party submission components.
- [x] Any copied code is attributed and used consistently with its license.
- [x] Model/service access complies with actual Nebius Token Factory terms.
- [x] Synthetic fixtures contain no private competition data, personal records, or copied restricted notebooks.
- [x] Demo footage and assets have appropriate rights.
- [x] Public release contains no credentials, private source snapshots, or hidden evaluation truth whose publication is restricted.
- [x] Any pre-existing components have an honest in-period contribution record.

## AI-assisted development record

Record source review and final responsibility for generated code. Follow the event's actual terms rather than assuming AI assistance is universally forbidden or automatically acceptable in every competition. Generated output still needs rights, dependency, and correctness review.

## Publication gate

Open a fresh browser session on the final repository. Confirm source, release tag, installation instructions, detected license, source assets, and attribution inventory. A repository existing on Ravi's machine is not evidence of public access.

The exact event obligations and original-work provisions remain in the [official rules](https://nebiusglobalaihackathon.devpost.com/rules). This file is a practical inventory, not a substitute for reading them.

## Assurance and research attribution

Deployment additions checked from installed metadata on 16 October: `@vercel/sandbox` 3.8.0 and Vercel CLI 64.3.1 declare Apache-2.0. Preserve their installed notices/licenses; the SDK is a server runtime dependency, while the CLI is development/deployment tooling. This does not complete the transitive dependency or cloud image/model rights review.

Record provenance/license for fixture source, constraint/check code, graph manifests, trusted mutation templates and any imported patch/trajectory. Keep synthetic invoices first-party and label them; do not import Ravi's other competition data or private repository code without rights review. The reference repairs and accepted task rules are original implementation assets, not copied competitor internals.

Official product documentation is cited by link in the research register. Paraphrase capabilities briefly; do not reproduce proprietary documentation, hidden prompts, logos or transcripts without applicable permission. A provider-neutral adapter does not imply affiliation or authorization from that product. Review any future tool transcript/patch publication under its terms and source rights.

The proposed first-party Apache-2.0 license does not license third-party model weights, SDKs, images or dependencies automatically. Add actual LICENSE/notice files in the implementation release, verify detectable licensing and record final model/image terms. The Markdown pack is not proof the future source has been licensed.
