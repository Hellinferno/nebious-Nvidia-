# License, ownership, and attribution work

Status: first-party Apache-2.0 `LICENSE` and `NOTICE` added at repository root on 16 October 2026. Publication, complete third-party inventory, model/image rights review and repository license detection remain release tasks.

## First-party license

Original BenchProof source, synthetic fixtures and documentation use the standard Apache-2.0 text in top-level [LICENSE](../../LICENSE), with scope notes in [NOTICE](../../NOTICE). This follows the existing release plan; the earlier suggestion of MIT was not adopted. The files remain local until the owner publishes them. Confirm ownership and repository license detection before publication.

Keep first-party code, fixture generation, UI assets, and original documentation distinct from third-party components. A permissive first-party license does not override dependencies' or model weights' terms.

## Inventory template

| Component | Source/version | License or terms | How used | Required notices | Checked |
| --- | --- | --- | --- | --- | --- |
| First-party BenchProof code | Local release preparation, 16 Oct | Apache-2.0 | Application | Top-level LICENSE/NOTICE added | Publication/detection pending |
| NVIDIA model | Actual model card/version | Actual model license | Remote inference or deployment | Record applicable terms | Pending |
| Python direct runtime packages | Installed metadata, 16 Oct: FastAPI 0.142.2, Pydantic 2.13.5, pydantic-settings 2.15.0 | MIT | Backend | Preserve installed license files | Metadata checked; transitive inventory pending |
| Python other runtime packages | Uvicorn 0.54.0, HTTPX 0.28.1, python-dotenv 1.2.4 | BSD-3-Clause | Backend | Preserve installed license files | Metadata checked; transitive inventory pending |
| OpenAI Python client | Installed 3.24.0 | Apache-2.0 | Nebius-compatible API client | Preserve installed license files | Metadata checked |
| JavaScript direct packages/tools | Lockfile: React/react-dom 19.3.0, Axios 1.20.0, Vite 8.3.2, oxlint 1.86.0, React plugin 6.1.1 | MIT | UI/build | Preserve package notices | Lock metadata checked; transitive inventory pending |
| TypeScript | Lockfile 6.0.3 | Apache-2.0 | UI type checking/build | Preserve package notices | Lock metadata checked |
| Contree client/SDK | Tested version | Actual package/repository license | Execution adapter | Record required attribution | Pending |
| Container base image | Digest/source | Actual image/component licenses | Runner environment | Record inventory | Pending |
| Service fixtures/checks | First-party generator commit | Chosen compatible license | Synthetic examples | Synthetic-data disclosure | Pending |
| Icons/fonts/media | Actual source/version | Actual asset terms | UI/video | Required credits | Pending |

## Ownership checks

- [ ] Ravi owns or has suitable rights to the first-party submission components.
- [ ] Any copied code is attributed and used consistently with its license.
- [ ] Model/service access complies with actual terms.
- [ ] Synthetic fixtures contain no private competition data, personal records, or copied restricted notebooks.
- [ ] Demo footage and music/assets have appropriate rights.
- [ ] Public release contains no credentials, private source snapshots, or hidden evaluation truth whose publication is restricted.
- [ ] Any pre-existing components have an honest in-period contribution record.

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
