param([Parameter(Mandatory)][string]$APE)
apebind inspect $APE --command-file "$PSScriptRoot/../binding/ffl.commands.yaml" --output "$PSScriptRoot/../binding/ffl.discovered.apebind.yaml"
exit $LASTEXITCODE
