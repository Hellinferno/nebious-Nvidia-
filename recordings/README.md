# Walkthrough provenance

`benchproof_demo_walkthrough.mp4` is a narrated browser walkthrough of a **saved
completed sample task**, not a continuous recording of newly performed inference.
The original recording script selects an existing completed task partway through.
Its review screens must not be presented as new approvals, execution or rollback.

The 21 October correction replaces the old narration and embedded/standalone
subtitles, removes the false signed-ZIP claim and unsupported claims about other
assistants, and adds a dated screenshot of the separate customized live rehearsal.
That final still is not moving footage of a second live execution. Its provenance
and exact two-call evidence are in [RELEASE_REHEARSAL.md](../RELEASE_REHEARSAL.md).
Narration is synthesized locally using Microsoft David, not a human testimonial.

Re-render from the retained original MP4 and dated local screenshot with
`powershell -File scratch/render_demo.ps1`; inspect the generated output before
using `-Publish` to replace the tracked MP4. Required input artifacts and the
original backup are local under `artifacts/` and are not part of a clean clone.
Audio, subtitles and final video are generated assets; the script never calls a
model or performs browser mutations. Do not run the legacy recording script as a
no-spend verification command: it creates drafts and requires private process-local
sample credentials. No owner capability should be hardcoded in recording source.

The clip is under three minutes, but the owner must still review the complete
video, rights/terms and final entry before submitting it. A video existing is not
evidence of actual competition submission or a user study.
