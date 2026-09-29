@echo off
cd /d "%~dp0.."
if not exist logs mkdir logs
set PYTHONUTF8=1
echo ===== %date% %time% >> logs\carga.log
uv run python -m copilot_suporte.carga >> logs\carga.log 2>&1