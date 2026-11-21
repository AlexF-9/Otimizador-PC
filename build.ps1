# Gera dist\OtimizadorPC.exe
# Uso:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Usa o lançador "py" se existir, senão "python" (ex.: GitHub Actions)
$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

& $python -m pip install --disable-pip-version-check -q -r requirements-build.txt
if (-not (Test-Path icone.ico)) { & $python gerar_icone.py }

& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name OtimizadorPC `
    --uac-admin `
    --icon icone.ico `
    --add-data "icone.ico;." `
    otimizador.py
if ($LASTEXITCODE -ne 0) { throw "O PyInstaller falhou." }

$exe = Get-Item dist\OtimizadorPC.exe
"Criado: $($exe.FullName) ($([math]::Round($exe.Length / 1MB, 1)) MB)"
