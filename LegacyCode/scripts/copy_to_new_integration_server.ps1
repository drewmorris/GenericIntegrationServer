<#
.SYNOPSIS
    Copies the minimal set of Onyx connector code, helpers, configs and tests
    into the local NewIntegrationServer folder so the new project starts with
    a green test-suite.

.DESCRIPTION
    • Run this script from the root of the Onyx repository (the directory that
      contains backend/, web/, NewIntegrationServer/).
    • The script uses RoboCopy to mirror selected directories so it is idempotent.
    • Adjust the $DestDir variable if you renamed the target folder.

.EXAMPLE
    PS> .\scripts\copy_to_new_integration_server.ps1
#>

param(
    [string]$DestDir  = "NewIntegrationServer",
    [string]$OnyxRoot = (Resolve-Path ".").Path
)

$SrcBackend = Join-Path $OnyxRoot "backend"
$DestRoot   = Join-Path $OnyxRoot $DestDir

# Ensure destination root exists
if (-not (Test-Path $DestRoot)) {
    New-Item -ItemType Directory -Path $DestRoot | Out-Null
}

# Helper for verbose RoboCopy with nicer headings
function Copy-Section {
    param(
        [string]$Label,
        [string]$Source,
        [string]$Target,
        [string]$Files = ""
    )
    Write-Host "`n==> $Label" -ForegroundColor Cyan
    if ($Files) {
        robocopy $Source $Target $Files /E /NFL /NDL /NJH /NJS /NC | Out-Null
    } else {
        robocopy $Source $Target /MIR /NFL /NDL /NJH /NJS /NC | Out-Null
    }
}

# 1. Connector runtime & all provider implementations
Copy-Section "Connectors runtime & providers" `
            (Join-Path $SrcBackend "onyx\connectors") `
            (Join-Path $DestRoot "connectors\onyx\connectors")

# 2. Generic utils referenced by connectors
Copy-Section "Utils" `
            (Join-Path $SrcBackend "onyx\utils") `
            (Join-Path $DestRoot "connectors\onyx\utils")

# 2.5 Access models – required by several connectors
Copy-Section "Access models" `
            (Join-Path $SrcBackend "onyx\access") `
            (Join-Path $DestRoot "connectors\onyx\access")

# 3. File-processing helpers (text extraction, etc.)
Copy-Section "File processing" `
            (Join-Path $SrcBackend "onyx\file_processing") `
            (Join-Path $DestRoot "connectors\onyx\file_processing")

# 4. Config modules (only selected files)
$SourceConfigs = Join-Path $SrcBackend "onyx\configs"
$TargetConfigs = Join-Path $DestRoot  "connectors\onyx\configs"
Copy-Section "Configs (constants, app_configs, llm_configs)" `
            $SourceConfigs $TargetConfigs "constants.py app_configs.py llm_configs.py __init__.py"

# 5. Tests – unit & integration
Copy-Section "Unit tests" `
            (Join-Path $SrcBackend "tests\unit\connectors") `
            (Join-Path $DestRoot "tests\unit\connectors")

Copy-Section "Integration tests" `
            (Join-Path $SrcBackend "tests\integration\connector_job_tests") `
            (Join-Path $DestRoot "tests\integration\connector_job_tests")

# 5b. Shared test utilities used by integration tests
Copy-Section "Integration test common_utils" `
            (Join-Path $SrcBackend "tests\integration\common_utils") `
            (Join-Path $DestRoot "tests\integration\common_utils")

# 6. Ensure namespace packages exist so imports resolve
$InitPaths = @(
    "connectors\__init__.py",
    "connectors\onyx\__init__.py",
    "connectors\onyx\connectors\__init__.py"
)
foreach ($rel in $InitPaths) {
    $full = Join-Path $DestRoot $rel
    if (-not (Test-Path $full)) {
        New-Item -ItemType File -Path $full | Out-Null
    }
}

Write-Host "`nAll done!  The connector code has been copied to $DestRoot." -ForegroundColor Green 