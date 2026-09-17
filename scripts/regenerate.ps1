param(
    [Parameter(Mandatory)]
    [string]$APE,

    [string]$APEBind = 'apebind'
)

$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$apePath = (Resolve-Path $APE).Path
$temporaryRoot = Join-Path $env:TEMP ("ffl-python-generated-" + [Guid]::NewGuid().ToString('N'))
$generatedPackage = Join-Path $temporaryRoot 'src\ffl'

try {
    & $APEBind generate "$projectRoot\binding\ffl.apebind.yaml" --ape $apePath --lang python --output $temporaryRoot
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    foreach ($path in @('_generated.py', '_runtime.py', 'py.typed', 'bin\ffl.com')) {
        Copy-Item -LiteralPath (Join-Path $generatedPackage $path) -Destination (Join-Path $projectRoot "src\ffl\$path") -Force
    }
}
finally {
    if (Test-Path $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
