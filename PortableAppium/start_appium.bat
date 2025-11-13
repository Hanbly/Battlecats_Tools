@echo off
:: ==========================================================
:: ==      THE FINAL, PRODUCTION-READY BATCH SCRIPT        ==
:: ==========================================================

:: STEP 1: Enable Delayed Expansion for robustness with special characters.
setlocal enabledelayedexpansion

:: STEP 2: Set current directory.
cd /d "%~dp0"

:: STEP 3: Set up PATH and ANDROID_HOME. THIS IS THE FINAL FIX.
title Portable Appium Server

:: Get a clean path for the current directory WITHOUT the trailing backslash.
set "PORTABLE_ROOT=%~dp0"
set "PORTABLE_ROOT=!PORTABLE_ROOT:~0,-1!"

:: Explicitly set the ANDROID_HOME environment variable for Appium to find ADB.
set "ANDROID_HOME=!PORTABLE_ROOT!"

:: Set the PATH for Node.js and platform-tools.
set "NODE_DIR=%~dp0node"
set "PATH=!NODE_DIR!;!PORTABLE_ROOT!\platform-tools;!PATH!"

echo Environment setup complete.
echo ANDROID_HOME is set to: !ANDROID_HOME!

:: STEP 4: DESTROY THE CACHED CONFIGURATION FILE.
set "CACHE_FILE=%~dp0node_modules\.cache\appium\extensions.yaml"
if exist "!CACHE_FILE!" (
    echo Found and deleting the culprit: !CACHE_FILE!
    del "!CACHE_FILE!"
)

:: STEP 5: Start Appium.
echo Starting Appium...
call "!NODE_DIR!\node.exe" "!__cd__!node_modules\appium\index.js" server --address 127.0.0.1 --port 4723 --use-drivers uiautomator2

endlocal