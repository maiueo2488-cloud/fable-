# タスクスケジューラから定期実行するためのラッパー。
# PowerShellの *>> リダイレクトはネイティブプロセスの出力を再エンコードして
# 文字化けすることがあるため、cmd.exeのリダイレクト(バイト列をそのまま追記)を使う。

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:PYTHONUTF8 = "1"
$LogPath = Join-Path $ProjectRoot "logs\discover.log"
Add-Content -Path $LogPath -Value "===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =====" -Encoding utf8

$pythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
cmd.exe /c "`"$pythonExe`" -m cli.discover >> `"$LogPath`" 2>&1"
