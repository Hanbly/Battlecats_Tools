@echo off
setlocal
cd /d "%~dp0"
set "NPM_CONFIG_CACHE=%~dp0_cache"
set "PATH=%~dp0node;%PATH%"
call "%~dp0node\npm.cmd" %*
endlocal