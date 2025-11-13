@echo off
setlocal
:: 临时将 node 目录添加到 PATH 环境变量
set "PATH=%~dp0node;%PATH%"


call "%~dp0node_modules\.bin\appium.cmd" %*

endlocal