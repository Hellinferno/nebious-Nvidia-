Add-Type -AssemblyName System.Speech

$narratives = @(
    @{
        file = "recordings\scene1_intro.wav"
        text = "Most AI coding assistants operate unconstrained: they suggest code that looks plausible but fails silently, overwrite test assertions to fake green results, or loop indefinitely on runtime errors. BenchProof treats code generation as a guarded engineering process with deterministic test isolation and immutable test protection, powered by NVIDIA Nemotron on Nebius Token Factory."
    },
    @{
        file = "recordings\scene2_intake.wav"
        text = "Here we select the StringCalculator project. Notice the strict boundary: application code in the app directory is editable, while test files in tests are completely protected and immutable. This prevents the model from cheating by weakening test assertions. We submit our task brief to fix negative number handling."
    },
    @{
        file = "recordings\scene3_plan.wav"
        text = "Before modifying any file, the agent inspects the code and queries NVIDIA Nemotron to generate a step-by-step implementation plan. We review the plan steps and approve it with an immutable cryptographic plan hash. Code cannot be mutated without explicit human approval."
    },
    @{
        file = "recordings\scene4_exec.wav"
        text = "The task runner executes a baseline check in an isolated Docker container, confirming the failing assertion. Next, NVIDIA Nemotron generates a surgical edit. The candidate is re-tested in a fresh container with network denied, strict memory limits, and process isolation. All tests pass, and the task reaches Review Ready."
    },
    @{
        file = "recordings\scene5_diff.wav"
        text = "We can inspect the unified diff showing the exact changes made to raise ValueError with the list of negative numbers. Every state mutation is recorded in a compare-and-swap checkpoint log, allowing instant rollback to any prior state without resetting budget limits."
    },
    @{
        file = "recordings\scene6_bundle.wav"
        text = "Finally, we export the complete verifiable evidence bundle: a signed ZIP archive containing the diff, full test logs, approved plan, and event trace. BenchProof is deployed and accessible live at benchproof.vercel.app, delivering reliable, guarded autonomous coding."
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
