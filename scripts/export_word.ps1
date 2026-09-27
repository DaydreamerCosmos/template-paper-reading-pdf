param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$inputTask = (Resolve-Path -LiteralPath $InputDocx).Path
$outputTask = [System.IO.Path]::GetFullPath($OutputPdf)
if ($inputTask -eq $outputTask) { throw 'Input and output must be different.' }
if ([System.IO.Path]::GetExtension($inputTask) -ne '.docx') { throw 'Input must be a DOCX working copy.' }
if ([System.IO.Path]::GetExtension($outputTask) -ne '.pdf') { throw 'Output must end with .pdf.' }
if ((Test-Path -LiteralPath $outputTask) -and -not $Force) { throw 'Output exists; choose another path or use -Force.' }
$sourceHashTask = (Get-FileHash -LiteralPath $inputTask -Algorithm SHA256).Hash
$parentTask = [System.IO.Path]::GetDirectoryName($outputTask)
[void][System.IO.Directory]::CreateDirectory($parentTask)
$wordTask = $null
$docTask = $null
try {
    $wordTask = New-Object -ComObject Word.Application
    $wordTask.Visible = $false
    $wordTask.DisplayAlerts = 0
    $wordTask.AutomationSecurity = 3
    $docTask = $wordTask.Documents.Open($inputTask, $false, $true)
    $docTask.ExportAsFixedFormat($outputTask, 17)
} finally {
    if ($null -ne $docTask) {
        $docTask.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($docTask)
    }
    if ($null -ne $wordTask) {
        $wordTask.Quit(0)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordTask)
    }
}
if ((Get-FileHash -LiteralPath $inputTask -Algorithm SHA256).Hash -ne $sourceHashTask) { throw 'Source changed during export.' }
if (-not (Test-Path -LiteralPath $outputTask) -or (Get-Item -LiteralPath $outputTask).Length -eq 0) { throw 'PDF export is missing or empty.' }
Write-Output "PDF exported: $outputTask. Rendering and visual review still required."
