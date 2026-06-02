@echo off
REM Arranque local: dev.cmd [db|bot|dashboard|all|stop]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev\dev.ps1" %*
