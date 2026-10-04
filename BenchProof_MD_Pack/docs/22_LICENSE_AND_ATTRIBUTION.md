# License, ownership, and attribution work

Status: release tasks. This document does not create the actual source-code license file required for the repository.

## Planned first-party license

Use Apache-2.0 for original BenchProof source unless Ravi chooses another compatible open-source license before publication. Add the exact standard text in top-level `LICENSE` and verify the repository recognizes it. Check owner/copyright fields that apply. Do not assume a Markdown planning file satisfies license detection.

Keep first-party code, fixture generation, UI assets, and original documentation distinct from third-party components. A permissive first-party license does not override dependencies' or model weights' terms.

## Inventory template

| Component | Source/version | License or terms | How used | Required notices | Checked |
| --- | --- | --- | --- | --- | --- |
| First-party BenchProof code | Final release commit | Planned Apache-2.0 | Application | Top-level license | Pending |
| NVIDIA model | Actual model card/version | Actual model license | Remote inference or deployment | Record applicable terms | Pending |
| Python dependencies | Locked versions | Per package | Backend/state/evaluator/testing | Preserve required notices | Pending |
| JavaScript dependencies | Lockfile | Per package | UI/build | Preserve required notices | Pending |
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

Record provenance/license for fixture source, constraint/check code, graph manifests, trusted mutation templates and any imported patch/trajectory. Keep synthetic invoices first-party and label them; do not import Ravi's other competition data or private repository code without rights review. The reference repairs and accepted task rules are original implementation assets, not copied competitor internals.

Official product documentation is cited by link in the research register. Paraphrase capabilities briefly; do not reproduce proprietary documentation, hidden prompts, logos or transcripts without applicable permission. A provider-neutral adapter does not imply affiliation or authorization from that product. Review any future tool transcript/patch publication under its terms and source rights.

The proposed first-party Apache-2.0 license does not license third-party model weights, SDKs, images or dependencies automatically. Add actual LICENSE/notice files in the implementation release, verify detectable licensing and record final model/image terms. The Markdown pack is not proof the future source has been licensed.
