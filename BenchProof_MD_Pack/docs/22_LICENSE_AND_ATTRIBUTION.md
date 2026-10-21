# License, ownership, and attribution work

Status: PARTIAL, rechecked 21 October 2026. First-party `LICENSE`/`NOTICE` exist and
the direct-package metadata below was inspected. This is not a complete transitive,
container, service-terms or ownership sign-off. Earlier checked boxes had no linked
owner attestation and are not relied upon as evidence. C-10 remains incomplete.

## First-party license

Original BenchProof source, synthetic fixtures and documentation use the standard Apache-2.0 text in top-level [LICENSE](../../LICENSE), with scope notes in [NOTICE](../../NOTICE). This follows the release plan; the earlier suggestion of MIT was not adopted.

Keep first-party code, fixture generation, UI assets, and original documentation distinct from third-party components. A permissive first-party license does not override dependencies' or model weights' terms.

## Inventory

| Component | Source/version | License or terms | How used | Required notices | Checked |
| --- | --- | --- | --- | --- | --- |
| First-party BenchProof code | Repository root | Apache-2.0 declared | Application | Top-level LICENSE/NOTICE | Files present; ownership attestation pending |
| NVIDIA model inference | Token Factory, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Exact model/service terms require owner review | Remote inference only; no weights redistributed | Review applicable model and account terms | Not signed off |
| Python direct runtime packages | FastAPI 0.142.2, Pydantic 2.13.5, pydantic-settings 2.15.0 | MIT | Backend | Preserve upstream notices as applicable | Installed metadata checked |
| Python network/server packages | Uvicorn 0.54.0, HTTPX 0.28.1, python-dotenv 1.2.4 | BSD-3-Clause | Backend | Preserve upstream notices as applicable | Installed metadata checked |
| OpenAI Python client | 3.24.0 | Apache-2.0 | Nebius-compatible API client | Preserve upstream notices as applicable | Installed metadata checked |
| Contree SDK/client | contree-sdk 0.3.6, contree-client 0.4.0 | Apache-2.0 | Installed alternative runner dependencies | Preserve upstream notices as applicable | Installed metadata checked; hosted route uses Docker |
| JavaScript direct packages | React/react-dom 19.3.0, Axios 1.20.0, Vite 8.3.3, oxlint 1.86.0 | MIT | UI/build | Preserve upstream notices as applicable | Installed package metadata checked |
| TypeScript | 6.0.3 | Apache-2.0 | UI build | Preserve upstream notices as applicable | Installed package metadata checked |
| Vercel Sandbox / CLI | `@vercel/sandbox` 3.8.0, CLI 64.7.0 | Apache-2.0 | Cloud runtime/development tooling | Preserve upstream notices as applicable | Installed package metadata checked |
| Container and installed packages | Dockerfile uses `python:3.12-slim`; actual built image identity is in execution evidence | Multiple component-specific terms | Isolated runner | Complete image/package review remains | Not signed off; a tag is not a digest pin |
| Synthetic fixtures / first-party SVG | Repository source | Apache-2.0 declared | Public samples and UI | Original/synthetic disclosure | Owner provenance attestation pending |
| Demo video / voice | Saved-task footage, dated screenshot, local Microsoft David narration | Asset/service rights require owner review | Submission media | Provenance in `recordings/README.md` | Technical media checks pass; rights not signed off |

## Ownership checks

- [ ] Owner confirms suitable rights to first-party submission components.
- [ ] Owner reviews copied code, source provenance and required attributions.
- [ ] Owner reviews applicable model and Nebius account/service terms.
- [ ] Owner confirms no restricted/private data in fixtures or submission materials.
- [ ] Owner reviews demo footage, synthetic-voice and other asset rights.
- [ ] Final public release content is reviewed for restricted information. Known-secret scans are scoped checks, not proof that every historical commit is secret-free.
- [ ] Owner confirms any pre-existing components and the in-period contribution statement.

Do not tick these on the owner's behalf. Direct metadata is useful inventory, not
a legal conclusion or proof that every transitive notice has been fulfilled.

## AI-assisted development record

Record source review and final responsibility for generated code. Follow the event's actual terms rather than assuming AI assistance is universally forbidden or automatically acceptable in every competition. Generated output still needs rights, dependency, and correctness review.

## Publication gate

The prior published baseline was confirmed at `a735384` and an independent
no-spend clean-clone startup/browser check passes. There is no release tag or actual
submitted-entry confirmation recorded. Check the final public source/assets,
detected license and owner attestations rather than inferring them from a local tree.

The exact event obligations and original-work provisions remain in the [official rules](https://nebiusglobalaihackathon.devpost.com/rules). This file is a practical inventory, not a substitute for reading them.

## Assurance and research attribution

Deployment additions checked from installed metadata on 16 October: `@vercel/sandbox` 3.8.0 and Vercel CLI 64.3.1 declare Apache-2.0. Preserve their installed notices/licenses; the SDK is a server runtime dependency, while the CLI is development/deployment tooling. This does not complete the transitive dependency or cloud image/model rights review.

Record provenance/license for fixture source, constraint/check code, graph manifests, trusted mutation templates and any imported patch/trajectory. Keep synthetic invoices first-party and label them; do not import Ravi's other competition data or private repository code without rights review. The reference repairs and accepted task rules are original implementation assets, not copied competitor internals.

Official product documentation is cited by link in the research register. Paraphrase capabilities briefly; do not reproduce proprietary documentation, hidden prompts, logos or transcripts without applicable permission. A provider-neutral adapter does not imply affiliation or authorization from that product. Review any future tool transcript/patch publication under its terms and source rights.

The repository's first-party Apache-2.0 declaration does not license third-party
weights, SDKs, images, dependencies or assets automatically. Root LICENSE/NOTICE
files are present; final model/image/service/asset review remains. This inventory
is not a legal opinion or owner eligibility/ownership attestation.
