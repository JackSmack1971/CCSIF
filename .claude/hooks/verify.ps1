# Thin platform entrypoint for the Phase 5B code-agnostic verify adapter.
# All parsing/execution logic lives in phase5b_verify.py so this dispatcher
# never hardcodes a language or toolchain; see that script's docstring for
# targets (full/lint/test/<slug>/rubric/citation/factcheck) and exit codes
# (0 pass, 1 fail, 2 unavailable).
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$adapter = Join-Path $scriptDir "../scripts/phase5b_verify.py"

python3 $adapter @args
exit $LASTEXITCODE
