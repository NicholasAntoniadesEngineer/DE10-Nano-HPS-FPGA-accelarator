@echo off
REM ============================================================================
REM Linux Driver Integration Script (Windows)
REM ============================================================================
REM Integrates calculator driver into existing Linux kernel build system
REM ============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\..
set DRIVER_SRC=%REPO_ROOT%\HPS\calculator_test

set KERNEL_DIR=
set INTEGRATION_TYPE=userspace
set DEVICE_TREE_DIR=
set OUTPUT_DIR=
set BASE_ADDRESS=0x00080000

REM Parse arguments
:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="-k" (
    set KERNEL_DIR=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--kernel-dir" (
    set KERNEL_DIR=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-t" (
    set INTEGRATION_TYPE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--type" (
    set INTEGRATION_TYPE=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-d" (
    set DEVICE_TREE_DIR=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--dtb-dir" (
    set DEVICE_TREE_DIR=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-o" (
    set OUTPUT_DIR=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--output-dir" (
    set OUTPUT_DIR=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-a" (
    set BASE_ADDRESS=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--base-address" (
    set BASE_ADDRESS=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage
echo ERROR: Unknown option: %~1
goto :usage

:args_done

REM Validate arguments
if "%KERNEL_DIR%"=="" (
    echo ERROR: Kernel directory is required
    goto :usage
)

if not exist "%KERNEL_DIR%" (
    echo ERROR: Kernel directory does not exist: %KERNEL_DIR%
    exit /b 1
)

if not exist "%DRIVER_SRC%" (
    echo ERROR: Driver source directory not found: %DRIVER_SRC%
    exit /b 1
)

echo ========================================
echo Calculator Driver Integration
echo ========================================
echo Kernel Directory:    %KERNEL_DIR%
echo Integration Type:    %INTEGRATION_TYPE%
echo Device Tree Dir:     %DEVICE_TREE_DIR%
echo Output Directory:    %OUTPUT_DIR%
echo Base Address:        %BASE_ADDRESS%
echo Driver Source:       %DRIVER_SRC%
echo.

REM Note: Windows batch script is limited. For full functionality, use the bash script
REM or run on Linux/WSL
echo.
echo NOTE: This is a Windows batch script stub.
echo For full integration functionality, please use:
echo   1. The bash script: integrate_linux_driver.sh (on Linux/WSL)
echo   2. Or manually copy files as documented in Docs/hps/linux_driver_development.md
echo.
echo Basic file locations:
echo   Driver header: %DRIVER_SRC%\calculator_driver.h
echo   Driver source: %DRIVER_SRC%\calculator_driver.c
echo.

exit /b 0

:usage
echo Usage: %~nx0 [OPTIONS]
echo.
echo Options:
echo   -k, --kernel-dir DIR    Linux kernel source directory ^(required^)
echo   -t, --type TYPE         Integration type: userspace or kernel
echo   -d, --dtb-dir DIR        Device tree source directory
echo   -o, --output-dir DIR     Output directory for generated files
echo   -a, --base-address ADDR  Calculator base address
echo   -h, --help               Show this help message
echo.
echo For full functionality, use integrate_linux_driver.sh on Linux/WSL
exit /b 1
