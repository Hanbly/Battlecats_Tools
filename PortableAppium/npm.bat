@echo off
setlocal
:: 关键步骤：临时将 node 目录添加到 PATH 环境变量的开头
set "PATH=%~dp0node;%PATH%"
:: 然后再执行 npm 命令
call "%~dp0node\npm.cmd" %*
endlocal