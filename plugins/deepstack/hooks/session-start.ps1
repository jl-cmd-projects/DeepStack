param(
    [Parameter(Position = 0)]
    [string]$Runtime = ""
)

$ErrorActionPreference = "Stop"

switch ($Runtime) {
    "claude" {
        if ([string]::IsNullOrEmpty($env:CLAUDE_PLUGIN_ROOT)) {
            [Console]::Error.WriteLine("session-start.ps1: CLAUDE_PLUGIN_ROOT is required")
            exit 2
        }
        $script:root = $env:CLAUDE_PLUGIN_ROOT
        if ([string]::IsNullOrEmpty($env:CLAUDE_CONFIG_DIR)) {
            $configDir = Join-Path $env:USERPROFILE ".claude"
        } else {
            $configDir = $env:CLAUDE_CONFIG_DIR
        }
        $script:sheet = Join-Path $configDir "deepstack-models.md"
    }
    "codex" {
        if ([string]::IsNullOrEmpty($env:CLAUDE_PLUGIN_ROOT)) {
            [Console]::Error.WriteLine("session-start.ps1: CLAUDE_PLUGIN_ROOT is required")
            exit 2
        }
        $script:root = $env:CLAUDE_PLUGIN_ROOT
        if ([string]::IsNullOrEmpty($env:CODEX_HOME)) {
            $configDir = Join-Path $env:USERPROFILE ".codex"
        } else {
            $configDir = $env:CODEX_HOME
        }
        $script:sheet = Join-Path $configDir "deepstack-models.md"
    }
    "copilot" {
        if ([string]::IsNullOrEmpty($env:COPILOT_PLUGIN_ROOT)) {
            [Console]::Error.WriteLine("session-start.ps1: COPILOT_PLUGIN_ROOT is required")
            exit 2
        }
        $script:root = $env:COPILOT_PLUGIN_ROOT
        if ([string]::IsNullOrEmpty($env:COPILOT_HOME)) {
            $configDir = Join-Path $env:USERPROFILE ".copilot"
        } else {
            $configDir = $env:COPILOT_HOME
        }
        $script:sheet = Join-Path $configDir "deepstack-models.md"
    }
    "cursor" {
        $script:root = Split-Path -Parent $PSScriptRoot
        $script:sheet = Join-Path $env:USERPROFILE ".cursor\deepstack-models.md"
    }
    default {
        [Console]::Error.WriteLine("session-start.ps1: unknown runtime '$Runtime'")
        exit 2
    }
}

if (Test-Path -LiteralPath $script:sheet) {
    foreach ($line in Get-Content -LiteralPath $script:sheet) {
        if ($line.TrimEnd("`r") -ceq "session hook: off") {
            if ($Runtime -eq "cursor") {
                Write-Output '{}'
            }
            exit 0
        }
    }
}

$mandate = "DeepStack: on a first task, read $script:root/skills/deepstack-mode/SKILL.md and follow it."
if ($Runtime -eq "copilot") {
    @{ additionalContext = $mandate } | ConvertTo-Json -Compress | Write-Output
} elseif ($Runtime -eq "cursor") {
    @{ additional_context = $mandate } | ConvertTo-Json -Compress | Write-Output
} else {
    Write-Output $mandate
}
