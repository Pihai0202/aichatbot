@echo off
title ZeroAI Local Studio - Qt 6 C++ Native Launcher
cd /d "%~dp0"

set PATH=C:\Qt6\6.8.0\msvc2022_64\bin;%PATH%

if not exist ZeroAI-Desk-CPP.exe (
    echo Building C++ Executable...
    call build_cpp.bat
)

if exist ZeroAI-Desk-CPP.exe (
    echo Starting ZeroAI Local Studio (Qt 6 C++ Native)...
    start ZeroAI-Desk-CPP.exe
) else (
    echo Error: ZeroAI-Desk-CPP.exe not found.
    pause
)
