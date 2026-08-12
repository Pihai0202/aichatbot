@echo off
title ZeroAI Local Studio - Qt C++ Compiler (CMake + MSVC)
cd /d "%~dp0"

echo [1/4] Initializing Visual Studio 2022 MSVC Environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat" x64

echo [2/4] Configuring CMake Project for Qt 6 C++...
"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" -B build -G "Visual Studio 17 2022" -A x64 -DCMAKE_PREFIX_PATH="C:/Qt6/6.8.0/msvc2022_64"

if %ERRORLEVEL% NEQ 0 (
    echo CMake Configuration failed!
    exit /b %ERRORLEVEL%
)

echo [3/4] Building Native Executable (Release)...
"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build build --config Release

if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo [4/4] Deploying Qt 6 Runtime Dynamic Libraries (windeployqt)...
copy /Y build\Release\ZeroAI-Desk-CPP.exe .
C:\Qt6\6.8.0\msvc2022_64\bin\windeployqt.exe --no-compiler-runtime ZeroAI-Desk-CPP.exe

echo.
echo ========================================================
echo SUCCESS! Built and Deployed ZeroAI-Desk-CPP.exe!
echo You can double-click ZeroAI-Desk-CPP.exe directly anytime!
echo ========================================================
