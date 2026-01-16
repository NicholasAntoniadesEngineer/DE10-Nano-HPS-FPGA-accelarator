@echo off
REM Generate QSys system before Quartus compilation
REM This must be run before compiling the project in Quartus

echo Generating QSys system...
qsys-generate soc_system.qsys --synthesis=VERILOG

if %ERRORLEVEL% EQU 0 (
    echo QSys generation completed successfully!
    echo You can now compile the project in Quartus.
) else (
    echo ERROR: QSys generation failed!
    echo Please check the error messages above.
    pause
    exit /b %ERRORLEVEL%
)
