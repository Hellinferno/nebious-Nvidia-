Add-Type -AssemblyName System.Speech

$narratives = @(
    @{
        file = "recordings\scene1_intro.wav"
        text = "Plausible code still needs tests and review. BenchProof is a coding agent for small Python projects, powered by NVIDIA Nemotron on Nebius Token Factory. This walkthrough reviews a saved sample task, rather than claiming a new live run. Plans, protected imported tests, isolated execution and bounded retries keep its work inspectable."
    },
    @{
        file = "recordings\scene2_intake.wav"
        text = "Here we select the StringCalculator sample. Application files in the app directory can be approved for editing. Imported tests stay protected from agent changes. The task asks for negative numbers to raise ValueError, while preserving empty input and positive sums. Only the calculator module is editable."
    },
    @{
        file = "recordings\scene3_plan.wav"
        text = "The saved task includes a model-generated implementation plan. Review the proposed steps and editable files before approval. The approved plan is bound to a recorded hash and source version. Implementation waits for approval; this recording is reviewing that completed task."
    },
    @{
        file = "recordings\scene4_exec.wav"
        text = "The recorded baseline fails its negative-number check. A real model edit is then tested in fresh Docker containers with network denied and resource limits. Candidate and fresh final checks pass, reaching Review Ready. Passing these supplied checks does not prove every requirement, so the patch still needs review."
    },
    @{
        file = "recordings\scene5_diff.wav"
        text = "The unified diff shows the negative-number validation and ValueError message. Saved checkpoints let the user restore a recorded task revision without resetting consumed budgets. This changes the task snapshot, not the user's local Git repository."
    },
    @{
        file = "recordings\scene6_bundle.wav"
        text = "Download the diff, approved plan, recorded checks and event trace together. The ZIP is not digitally signed; review its contents before sharing. BenchProof runs at benchproof dot vercel dot app. Skills, harness choices and read-only documentation context are also available in the newer release."
    }
    @{
        file = "recordings\scene7_customization.wav"
        text = "This dated screenshot shows the separate October twenty-first rehearsal. A pinned skill, single-pass harness and consented documentation reference accompanied two genuine model calls, one patch and three isolated executions. It is one public sample, not a held-out benchmark."
    }
)

foreach ($item in $narratives) {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.SelectVoice("Microsoft David Desktop")
    $synth.Rate = 0
    $synth.SetOutputToWaveFile($item.file)
    $synth.Speak($item.text)
    $synth.Dispose()
    Write-Host "Generated: $($item.file)"
}
