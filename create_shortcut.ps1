# Cree un raccourci "P.R.O.S.P.E.R" sur le Bureau (lance la GUI sans terminal).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root "venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source } else { Write-Host "pythonw.exe introuvable. Lancez install_gui.bat d'abord."; exit 1 }
}
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path $desktop "P.R.O.S.P.E.R.lnk"))
$lnk.TargetPath = $py
$lnk.Arguments = '"' + (Join-Path $root "run_gui.pyw") + '"'
$lnk.WorkingDirectory = $root
$ico = Join-Path $root "assets\icons\prosper.ico"
if (Test-Path $ico) { $lnk.IconLocation = $ico }
$lnk.Description = "P.R.O.S.P.E.R - Personal AI Assistant"
$lnk.Save()
Write-Host "Raccourci cree sur le Bureau : P.R.O.S.P.E.R"
